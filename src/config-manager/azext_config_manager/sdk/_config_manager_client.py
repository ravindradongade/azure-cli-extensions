from typing import Any, TYPE_CHECKING

from azure.core.pipeline import policies
from azure.core.rest import HttpRequest, HttpResponse
from azure.core.utils import case_insensitive_dict
from azure.mgmt.core import ARMPipelineClient
from azure.mgmt.core.policies import ARMAutoResourceProviderRegistrationPolicy

import json
import uuid

from ._configuration import ConfigManagerClientConfiguration

class ConfigManagerClient:

    def __init__(
        self,
        credential: "TokenCredential",
        subscription_id: str,
        base_url: str = "https://management.azure.com",
        **kwargs: Any
    ) -> None:
        self._config = ConfigManagerClientConfiguration(
            credential=credential, subscription_id=subscription_id, **kwargs
        )
        _policies = kwargs.pop("policies", None)
        if _policies is None:
            _policies = [
                policies.RequestIdPolicy(**kwargs),
                self._config.headers_policy,
                self._config.user_agent_policy,
                self._config.proxy_policy,
                policies.ContentDecodePolicy(**kwargs),
                ARMAutoResourceProviderRegistrationPolicy(),
                self._config.redirect_policy,
                self._config.retry_policy,
                self._config.authentication_policy,
                self._config.custom_hook_policy,
                self._config.logging_policy,
                policies.DistributedTracingPolicy(**kwargs),
                policies.SensitiveHeaderCleanupPolicy(**kwargs) if self._config.redirect_policy else None,
                self._config.http_logging_policy,
            ]
        self._client: ARMPipelineClient = ARMPipelineClient(base_url=base_url, config=self._config, **kwargs)
    
    def assign_role_to_solution_bindings(self, resource_group, deployment_target, role_id, principal_id):
        matching_binding_ids = self._get_matching_bindings_ids(resource_group, deployment_target)
        
        # Assign role with scope of the DT
        dt_id = f"/subscriptions/{self._config.subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Edge/deploymentTargets/{deployment_target}"
        self._assign_role_on_resource(dt_id, role_id, principal_id)
        
        # Assign role with scope of the bindings
        for binding in matching_binding_ids:
            self._assign_role_on_resource(binding, role_id, principal_id)
    
    def remove_role_from_solution_bindings(self, resource_group, deployment_target, role_id, principal_id):
        matching_binding_ids = self._get_matching_bindings_ids(resource_group, deployment_target)

        # Remove role with scope of the DT
        dt_id = f"/subscriptions/{self._config.subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Edge/deploymentTargets/{deployment_target}"
        self._remove_role_on_resource(dt_id, role_id, principal_id)
        
        # Remove role with scope of the bindings
        for binding in matching_binding_ids:
            self._remove_role_on_resource(binding, role_id, principal_id)
        

    def _get_matching_bindings_ids(self, resource_group, deployment_target):
        _url = f"/subscriptions/{self._config.subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Edge/solutionBindings"
        req = self._construct_http_get_request(_url)
        resp = self._client.send_request(req)
        resp_dict = json.loads(resp.text())
        try:
            #extract solution binding ids with matching DT
            matching_binding_ids = []
            for sb in resp_dict["value"]:
                dt_id = sb["properties"]["deploymentTarget"]
                dt_name = dt_id.split('/')[-1]
                if dt_name == deployment_target:
                    matching_binding_ids.append(sb["id"])
            return matching_binding_ids
        except Exception as e:
            print(f"Error in processing solution bindings:\n")
            raise e
        
    def _assign_role_on_resource(self, arm_id, role_id, principal_id):
        try:
            # Ignore the first '/'
            scope = arm_id[1:]
            uuid_for_role = str(uuid.uuid4())
            role_assignment_url = f"/{scope}/providers/Microsoft.Authorization/roleAssignments/{uuid_for_role}?api-version=2022-04-01"
            payload = {}
            payload["properties"] = {}
            payload["properties"]["roleDefinitionId"] = f"/{scope}/providers/Microsoft.Authorization/roleDefinitions/{role_id}"
            payload["properties"]["principalId"] = f"{principal_id}"
            req = self._construct_http_put_request(role_assignment_url, payload)
            resp = self._client.send_request(req)
            if resp.status_code != 201:
                print(f"Response code status was {resp.status_code} for assigning role on scope {scope}: {resp.text()}")
            else:
                print(f"Assigned role at {role_assignment_url}")
        except Exception as e:
            print(f"Error in assigning role on scope {scope}\nException: {e}")
            raise e

    def _remove_role_on_resource(self, arm_id, role_id, principal_id):
        try:
            # Ignore the first '/'
            scope = arm_id[1:]
            role_assignments_url = f"/{scope}/providers/Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            req = self._construct_http_get_request(role_assignments_url)
            resp = self._client.send_request(req)
            if resp.status_code != 200:
                print(f"Response code status was {resp.status_code} when retreiving assignments on scope {scope}: {resp.text()}")
            else:
                resp_dict = json.loads(resp.text())
                for role_ass in resp_dict["value"]:
                    fetched_role_id = role_ass["properties"]["roleDefinitionId"].split('/')[-1]
                    fetched_principal_id = role_ass["properties"]["principalId"]
                    if fetched_principal_id == principal_id and fetched_role_id == role_id:
                        req = self._construct_http_delete_request(role_ass["id"] +"?api-version=2022-04-01")
                        resp = self._client.send_request(req)
                        if resp.status_code != 200:
                            print(f"Response code status was {resp.status_code} when removing role for {arm_id}: {resp.text()}")
                        else:
                            print(f"Successfully removed role {role_ass["id"]}") 
        except Exception as e:
            print(f"Error in removing role on scope {scope}\nException: {e}")
            raise e

    def _construct_http_put_request(self, url, body):
        _headers, _params = self._construct_http_headers()
        req = HttpRequest(method="PUT", url=url, params=_params, headers=_headers, json=body)
        req.url = self._client.format_url(req.url)
        return req


    def _construct_http_get_request(self, url):
        _headers, _params = self._construct_http_headers()
        req = HttpRequest(method="GET", url=url, params=_params, headers=_headers)
        req.url = self._client.format_url(req.url)
        return req
    
    def _construct_http_delete_request(self, url):
        _headers, _params = self._construct_http_headers()
        req = HttpRequest(method="DELETE", url=url, params=_params, headers=_headers)
        req.url = self._client.format_url(req.url)
        return req
    
    def _construct_http_headers(self):
        _headers = case_insensitive_dict({})
        _params = case_insensitive_dict({})

        api_version: str = self._config.api_version
        accept =  "application/json"

        # Construct parameters
        _params["api-version"] = api_version

        # Construct headers
        _headers["Accept"] = accept
        return _headers, _params