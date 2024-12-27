from . import SlotLockWorld
from CommonClient import ClientCommandProcessor, CommonContext, logger, server_loop, gui_enabled, get_base_parser
from NetUtils import ClientStatus
try:
    from NetUtils import HintStatus
except ImportError:
    pass
import asyncio
class SlotLockContext(CommonContext):

    # Text Mode to use !hint and such with games that have no text entry
    tags = CommonContext.tags
    game = "SlotLock"  # empty matches any game since 0.3.2
    items_handling = 0b111  # receive all items for /received
    want_slot_data = True
    checking_hints = False
    def __init__(self, server_address=None, password=None):
        CommonContext.__init__(self, server_address, password)
    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super(TextContext, self).server_auth(password_requested)
        await self.get_username()
        await self.send_connect()
    async def check_hints(self):
        while self.checking_hints:
            await asyncio.sleep(1)
        self.checking_hints = True
        if f"_read_hints_{self.team}_{self.slot}" in self.stored_data:
            hintdata = self.stored_data[f"_read_hints_{self.team}_{self.slot}"]
            hinted_count = {}
            loc_count = {}
            real_hint_cost = max(1, int(self.hint_cost * 0.01 * self.total_locations))
            for location in self.server_locations:
                if location // 10 in loc_count:
                    loc_count[location // 10] += 1
                else:
                    loc_count[location // 10] = 1
            for hint in hintdata:
                if self.slot_concerns_self(hint["receiving_player"]):
                    if hint["item"] not in hinted_count:
                        hinted_count[hint["item"]] = 1
                    else:
                        hinted_count[hint["item"]] += 1
                    if any(item.item == hint["item"] for item in self.items_received):
                        if hasattr(self, "update_hint"):
                            self.update_hint(hint["location"],hint["finding_player"], HintStatus.HINT_NO_PRIORITY)
            for hint in hintdata:
                if self.slot_concerns_self(hint["finding_player"]):
                    if hint["location"]//10 not in hinted_count:
                        hinted_count[hint["location"]// 10] = 0
                    if (not "status" in hint) or hint["status"] == HintStatus.HINT_PRIORITY:
                        if not any(item.item == hint["location"]//10 for item in self.items_received) and not hint["found"] and hinted_count[hint["location"]//10] < loc_count[hint["location"]//10]:
                            if self.hint_points >= real_hint_cost and self.auto_hint_locked_items:
                                await self.send_msgs([{"cmd": "Say", "text": f"!hint {self.item_names.lookup_in_game(hint["location"]//10, "SlotLock")}"}])
                                break
        await asyncio.sleep(1)
        self.checking_hints = False
    def update_auto_locations(self):
        for location in self.missing_locations:
            if any(item.item == location // 10 for item in self.items_received) or (location >= 10000 and self.free_starting_items):
                self.locations_checked.add(location)
            else:
                #print(f"Don't yet have {self.location_names.lookup_in_game(location,"SlotLock")}, required item {self.item_names.lookup_in_game(location // 10)}")
                pass


    def on_package(self, cmd: str, args: dict):
        asyncio.create_task(self.check_hints())
        if cmd == "Connected":
            self.game = self.slot_info[self.slot].game
            self.free_starting_items = args["slot_data"]["free_starting_items"]
            try:
                self.auto_hint_locked_items = args["slot_data"]["auto_hint_locked_items"]
            except KeyError:
                self.auto_hint_locked_items = True
        if cmd == "ReceivedItems" or cmd == "Connected" or cmd == "RoomUpdate":
            self.update_auto_locations()
            asyncio.create_task(self.send_msgs([{"cmd": "LocationChecks",
                         "locations": list(self.locations_checked)}]))
            victory = True
            if len(self.missing_locations) > 0:
                victory = False
            else:
                for i, name in enumerate(self.player_names):
                    success = False
                    for item in self.items_received:
                        print(item)
                        if i == 0 or item.item == i + 1000:
                            success = True
                    if not success:
                        victory = False
            if victory:
                print("Victory!")
                self.finished_game = True
                asyncio.create_task(self.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}]))

    async def disconnect(self, allow_autoreconnect: bool = False):
        await super().disconnect(allow_autoreconnect)
        self.finished_game = False
        self.free_starting_items = False
        self.auto_hint_locked_items = False
        self.update_auto_locations()

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
        import urllib
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
