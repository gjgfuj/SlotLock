from . import SlotLockWorld
from CommonClient import ClientCommandProcessor, CommonContext, logger, server_loop, gui_enabled, get_base_parser
from NetUtils import ClientStatus
import asyncio
class SlotLockContext(CommonContext):

    # Text Mode to use !hint and such with games that have no text entry
    tags = CommonContext.tags
    game = "SlotLock"  # empty matches any game since 0.3.2
    items_handling = 0b111  # receive all items for /received
    want_slot_data = True
    def __init__(self, server_address=None, password=None):
        CommonContext.__init__(self, server_address, password)
    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(TextContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
    def update_auto_locations(self):
        self.locations_checked = [location for location in self.missing_locations if location > 10000 or any(item.item == location // 10 for item in self.items_received)]
    def on_package(self, cmd: str, args: dict):
        print(f"on_package: {cmd}, {args}")
        if cmd == "Connected":
            self.game = self.slot_info[self.slot].game
            self.update_auto_locations()
            asyncio.create_task(self.send_msgs([{"cmd": "LocationChecks",
                         "locations": list(self.locations_checked)}]))
        if cmd == "ReceivedItems" or cmd == "Connected":
            self.update_auto_locations()
            asyncio.create_task(self.send_msgs([{"cmd": "LocationChecks",
                         "locations": list(self.locations_checked)}]))
            victory = True
            for i, name in enumerate(self.player_names):
                success = False
                for item in self.items_received:
                    print(item)
                    if i == 0 or item.item == i:
                        success = True
                if not success:
                    print(f"No victory without {self.player_names[i]}")
                    victory = False
            if victory:
                print("Victory!")
                self.finished_game = True
                asyncio.create_task(self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]))

    async def disconnect(self, allow_autoreconnect: bool = False):
        await super().disconnect(allow_autoreconnect)
        self.finished_game = False

def launch(*args):

    async def main(args):
        ctx = SlotLockContext(args.connect, args.password)
        ctx.auth = args.name
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="server loop")

        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()

        await ctx.exit_event.wait()
        await ctx.shutdown()

    import colorama

    parser = get_base_parser(description="SlotLock Archipelago Client, for text interfacing.")
    parser.add_argument('--name', default=None, help="Slot Name to connect as.")
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    args = parser.parse_args(args)

    # handle if text client is launched using the "archipelago://name:pass@host:port" url from webhost
    if args.url:
        url = urllib.parse.urlparse(args.url)
        if url.scheme == "archipelago":
            args.connect = url.netloc
            if url.username:
                args.name = urllib.parse.unquote(url.username)
            if url.password:
                args.password = urllib.parse.unquote(url.password)
        else:
            parser.error(f"bad url, found {args.url}, expected url in form of archipelago://archipelago.gg:38281")

    # use colorama to display colored text highlighting on windows
    colorama.init()

    asyncio.run(main(args))
    colorama.deinit()
