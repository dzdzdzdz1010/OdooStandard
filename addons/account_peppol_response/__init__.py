from . import models
from . import wizard


def _account_peppol_response_post_init(env):
    env['account_edi_proxy_client.user']._peppol_auto_register_services('account_peppol_response')


def _account_peppol_response_uninstall(env):
    env['account_edi_proxy_client.user']._peppol_auto_deregister_services('account_peppol_response')
