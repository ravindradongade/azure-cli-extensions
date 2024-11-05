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
        except Exception as e:
            print(f"Error in processing solution bindings:\n")
            raise e
        
        # Assign role with scope of the bindings


    def _construct_http_get_request(self, url):
        _headers = case_insensitive_dict({})
        _params = case_insensitive_dict({})

        api_version: str = self._config.api_version
        accept =  "application/json"

        # Construct parameters
        _params["api-version"] = api_version

        # Construct headers
        _headers["Accept"] = accept

        req = HttpRequest(method="GET", url=url, params=_params, headers=_headers)
        req.url = self._client.format_url(req.url)
        return req