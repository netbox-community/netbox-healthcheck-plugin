from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link='plugins:netbox_healthcheck_plugin:healthcheck_view',
        link_text='HealthCheck',
        buttons=plugin_buttons
    ),
)
