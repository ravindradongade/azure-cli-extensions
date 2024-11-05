from typing import Any, TYPE_CHECKING

from azure.core.pipeline import policies
from azure.core.rest import HttpRequest, HttpResponse
from azure.core.utils import case_insensitive_dict
from azure.mgmt.core import ARMPipelineClient
from azure.mgmt.core.policies import ARMAutoResourceProviderRegistrationPolicy

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
        print(base_url)
        self._client: ARMPipelineClient = ARMPipelineClient(base_url=base_url, config=self._config, **kwargs)
    
    def get_all_solution_bindings(self, rg):
        _url = f"/subscriptions/{self._config.subscription_id}/resourceGroups/{rg}/providers/Microsoft.Edge/solutionBindings"

        _headers = case_insensitive_dict({})
        _params = case_insensitive_dict({})

        api_version: str = self._config.api_version
        accept =  "application/json"

        # Construct parameters
        _params["api-version"] = api_version

        # Construct headers
        _headers["Accept"] = accept

        req = HttpRequest(method="GET", url=_url, params=_params, headers=_headers)
        req.url = self._client.format_url(req.url)
        resp = self._client.send_request(req)
        print(resp)
        print(resp.text())
