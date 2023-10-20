import requests

class BearerAuth(requests.auth.AuthBase):
    """ 
    Authentication with bearer.
    token::str = jwt_token 

    """

    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r
    

class Mango:

    def __init__(self, endpoint):

        self.predefined = {
            "group":"name",
            "appellation":"name",
            "source":"title"
        }
        self.base_url = endpoint
    
    def authenticate(self, user, password):

        """ 
        Authenticate to the server using username and password 
        and save the access token for later usage.
        """

        token = requests.post(
            self.base_url + "users/authenticate",
            json={
                "username": user,
                "password": password
                }
            ).json()["jwtToken"]
        
        self.jwt_token = token


    def get_active_entities(self):

        """ 
        Retrieve active entity types and their names as displayed in Era.
        """

        response = requests.get(
            self.base_url+"entity/get?collectionName=types&active=true", 
            auth=BearerAuth(self.jwt_token)
            ).json()
        
        self.active_entities = {
                e["displayName"].lower():e["name"]
                for e in response["result"]
                }
        
    def get_relationTypes(self):

        """Retrieve all active relation types from db."""

        response = requests.get(
            self.base_url + "relation/getActiveRelationTypes",
            auth=BearerAuth(self.jwt_token)
            ).json()["result"]
        
        all_types = {
            r["name"] + r["type"]["name"] + r["relationType"]["name"] : r["_id"] for r in response
            }
        self.relation_types = all_types


    def get_relations(self):

        """Retrieve all active relations from db."""

        response = requests.get(
            self.base_url + f'relation/get',
            auth = BearerAuth(self.jwt_token)
            ).json()["result"]
        
        self.relations = {
            rel["entity1"] + rel["entity2"] + rel["relationType"] : rel["_id"] for rel in response if all(
                list(
                    map(lambda x: isinstance(rel.get(x), str), ["entity1", "entity2", "relationType"])
                    )
                )
            }


    def get_entity_id(self, entity_type, params_dict):

        """ 
        Retrieve the entity ID using a selection of fields

        Args:
            entity_type: str = `name` of the entityType to query
            params_dict: Dict[field_name:value] = a dictionary of key-value pairs to use as a query selector
        
        """

        query_selector = "&".join([f"{field_name}={value}" for field_name, value in params_dict.items()])
        get_url = self.base_url + f"entity/get?collectionName={entity_type}&{query_selector}"
        response = requests.get(
            get_url,
            auth=BearerAuth(self.jwt_token)
            ).json()

        try:
            if (out:=response["result"]):
                return out[0].get("_id") 
            else:
                return out

        except KeyError:
            raise KeyError(str(response))



    def merge_entity(self, display_name, entity_name, params=None):

        """ 
        Create a new entity OR match the existing one.

        Args:
            display_name:str = name of the entityType as displayed in Era
            entity_name:str = unique entity identifier 
            params:Dict[field_name:value] = a dictionary of additional entity properties

        """        
        
        if not hasattr(self, "active_entities"):
            self.get_active_entities()
        
        if params is None:
            params = {}

        display_name = display_name.lower()
        entity_type = self.active_entities.get(display_name)

        if entity_type == "appellation":
            params.update(
                {
                    "appellationType":self.get_entity_id("types", {"name": "object"})
                    }
                )
        field_name = out if (out:=self.predefined.get(display_name)) else "description"
        params.update({field_name:entity_name})

        entity_id = self.get_entity_id(entity_type, params)
        if entity_id:
            return entity_id
        else:
            params.update({"active": True})
            body  = {
                "collectionName": entity_type, 
                "value": params    
                }
            return requests.post(
                self.base_url + "entity/create",
                json=body,
                auth = BearerAuth(self.jwt_token)
                ).json()["_id"]
    


    def update_entity(self, display_name, entity_name, params=None):
        
        """ Update an existing entity or return the existing ID.  """

        if params is None:
            params = {}

        display_name = display_name.lower()
        entity_type = self.active_entities.get(display_name)
        field_name = out if (out:=self.predefined.get(display_name)) else "description"
        
        params.update({field_name:entity_name})
        entity_id = self.get_entity_id(entity_type, params)
        
        if not entity_id:
            raise BaseException(f"Cannot update a not existing entity: `{entity_name}`.")

        else:
            body  = {
                "collectionName": entity_type,
                "id":entity_id,
                "value":params
                }
            
            return requests.post(
                self.base_url + "entity/update",
                json=body,
                auth = BearerAuth(self.jwt_token)
                ).json()
    

    def merge_relation(
            self,
            relation_type,
            src_type,
            trg_type,
            entity1,
            entity2
            ):
        """
        Create or match a named relation between 2 specified entities.

        Args:
            relation_type:str = name of the relation to be created
            scr_type:str = `name` of the entityType for the source entity
            trg_type:str = `name` of the entityType for the target entity
            entity1:str = mongodb ID of the source entity
            entity2:str = mongodb ID of the target entity

        """
        if not hasattr(self, "relation_types"):
            self.get_relationTypes()
       
        # retrieve or create a relationType between two specified entityTypes       
        if (out := relation_type + src_type + trg_type) in self.relation_types:
            relation_type_id = self.relation_types[out]
    
        else:
            src_type_id = self.get_entity_id("types", {"name": src_type})
            trg_type_id = self.get_entity_id("types", {"name": trg_type})

            body = { 
                "value": {
                    "active": True,
                    "name": relation_type,
                    "type": src_type_id, 
                    "relationType": trg_type_id
                    }
                }

            response = requests.post(
                self.base_url + "relation/createRelationType",
                json=body,
                auth=BearerAuth(self.jwt_token)
                ).json()

            relation_type_id = response["_id"] 
            self.relation_types.update({relation_type + src_type + trg_type:relation_type_id})
    
        
        if not hasattr(self, "relations"):
            self.get_relations()
        
        # check if the relation exists 
        if (out:=entity1+entity2+relation_type_id) in self.relations:
            return self.relations[out]
        
        else:  
            body = {
                "value":
                {
                    "active": True,
                    "entity1": entity1, 
                    "relationType": relation_type_id,
                    "entity2": entity2
                }
            }
            relation = requests.post(
                self.base_url + "relation/create",
                json=body,
                auth=BearerAuth(self.jwt_token)
                ).json()

            self.relations.update({entity1+entity2+relation_type_id:relation["_id"]})
            return relation["_id"]
        
    
