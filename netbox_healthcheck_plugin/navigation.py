from netbox.plugins import PluginMenuButton, PluginMenuItem


menu_items = (
    PluginMenuItem(
        link='plugins:netbox_healthcheck_plugin:healthcheck_list',
        link_text='HealthCheck',
        buttons=None
    ),
)
