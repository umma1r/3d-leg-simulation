from trame.app import get_server
from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.widgets import html

# trame-vuetify uses Vue 2
server = get_server(client_type="vue2")

# Build UI using the layout's content slot
with SinglePageWithDrawerLayout(server, title="Hello trame") as layout:
    with layout.content:
        html.Div("hello from trame 👋", classes="pa-6 text-h5")

if __name__ == "__main__":
    server.start(address="0.0.0.0", port=8000, open_browser=False)
