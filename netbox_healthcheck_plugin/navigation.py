from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices


plugin_buttons = [
    PluginMenuButton(
        link='plugins:netbox_healthcheck_plugin:healthcheck_add',
        title='Add',
        icon_class='mdi mdi-plus-thick',
        color=ButtonColorChoices.GREEN
    )
]

menu_items = (
    PluginMenuItem(
        link='plugins:netbox_healthcheck_plugin:healthcheck_list',
        link_text='HealthCheck',
        buttons=plugin_buttons
    ),
)
