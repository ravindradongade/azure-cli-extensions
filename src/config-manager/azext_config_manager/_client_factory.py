# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

def cf_cosmosdb_preview(cli_ctx, *_):
    from azure.cli.core.commands.client_factory import get_mgmt_service_client
    from azext_config_manager.sdk._config_manager_client import ConfigManagerClient
    return get_mgmt_service_client(cli_ctx, ConfigManagerClient)