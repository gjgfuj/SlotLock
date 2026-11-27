import logging
from math import floor
from typing import Any, Dict, Set, List, TextIO

import Fill
from BaseClasses import CollectionState, Item, ItemClassification, Location, MultiWorld, Region, LocationProgressType
import worlds
from worlds import AutoWorld
from worlds.LauncherComponents import Component, components, icon_paths, launch_subprocess, Type
from NetUtils import Hint, SlotType
from .Options import *

def launch_client(*args):
    from .Client import launch
    from CommonClient import gui_enabled
    if not gui_enabled:
        print(args)
        launch(args)
    launch_subprocess(launch, name="SlotLockClient", args=args)
components.append(Component("Slot Lock Client", "SlotLockClient", func=launch_client,
                            component_type=Type.CLIENT, supports_uri=True, game_name="SlotLock",
                            icon="slotlock_icon"))

icon_paths["slotlock_icon"] = f"ap:{__name__}/icons/Slotlock_by_Ruby3440.png"

class LockItem(Item):
    coin_suffix = "" #I forget what this is here for
    def __init__(self, world: "SlotLockWorld", player: int):
        Item.__init__(self,f"Unlock {world.multiworld.worlds[player].player_name}",ItemClassification.progression,player+1001,world.player)
        self.game = "SlotLock"
        self.unlock_player = player
class LockLocation(Location):
    pass


class SlotLockWebWorld(AutoWorld.WebWorld):
    theme = "ice"
    tutorials = []

    option_groups = option_groups
class SlotLockWorld(AutoWorld.World):
    """Locks other player slots."""

    game = "SlotLock"
    options: SlotLockOptions
    options_dataclass = SlotLockOptions
    location_name_to_id = {f"Lock_{num+1}": num+10010 for num in range(50000)}
    item_name_to_id = {f"Unlock_{num+1}": num+1001 for num in range(5000)}
    item_name_to_id["Nothing"] = 6999
    multiworld : MultiWorld
    web = SlotLockWebWorld()
    for i in range(1000):
        item_name_to_id[f"Unlock Bonus Slot {i+1}"] = i + 1
        for j in range(10):
            location_name_to_id[f"Bonus Slot {i+1}{" " + str(j+1) if j > 0 else ""}"] = i*10 + j + 10
    item_name_groups = {"Slot Unlocks": set(f"Unlock_{num+1}" for num in range(5000)), "Bonus Slot Unlocks": set(f"Unlock Bonus Slot {num+1}" for num in range(1000))}
    location_name_groups = {"Slot Rewards": set(f"Lock_{num+1}" for num in range(50000)), "Bonus Slot Rewards": set([f"Bonus Slot {(num+10)//10}{" " + str((num % 10)+1) if (num % 10) > 0 else ""}" for num in range(1000)])}
    slots_to_lock = []
    recursive_locks = []
    associated_worlds = set()
    sphere_unlocks = {}
    slot_locking_items = []
    def __init__(self, multiworld, player):
        super().__init__(multiworld, player)
    def create_item(self, name: str):
        try:
            if "Unlock_" in name:
                return self.create_slotlock_item(self.multiworld.player_name[int(name.split("_")[1])])
            elif "Unlock Bonus Slot" in name:
                return self.create_bonus_key(int(name.lstrip("Unlock Bonus Slot ")))
            elif "Unlock " in name:
                return self.create_slotlock_item(name.lstrip("Unlock "))
            elif name == "Nothing":
                return Item(name,ItemClassification.filler,6999, self.player)
        except KeyError:
            pass
        raise Exception(f"Invalid item name: {name}")
    @classmethod
    def stage_generate_early(cls, multiworld: "MultiWorld"):
        item_name_to_id = {}
        location_name_to_id = {}
        world_unlock_items = set()
        world_unlock_locations = set()
        bonus_locations = set()
        bonus_items = set()
        for id, world in multiworld.worlds.items():
            if multiworld.player_types[id] == SlotType.player:
                item_name_to_id[f"Unlock {world.player_name}"] = id + 1001
                world_unlock_items.add(f"Unlock {world.player_name}")
                for i in range(10):
                    location_name_to_id[f"Free Item {world.player_name} {i+1}"] = id*10 + i + 10010
                    world_unlock_locations.add(f"Free Item {world.player_name} {i+1}")
        item_name_to_id["Nothing"] = 6999
        for i in range(1000):
            item_name_to_id[f"Unlock Bonus Slot {i+1}"] = i + 1
            bonus_items.add(f"Unlock Bonus Slot {i+1}")
            for j in range(10):
                location_name_to_id[f"Bonus Slot {i+1}{" " + str(j+1) if j > 0 else ""}"] = i*10 + j + 10
                bonus_locations.add(f"Bonus Slot {i+1}{" " + str(j+1) if j > 0 else ""}")
        cls.item_name_to_id = item_name_to_id
        cls.location_name_to_id = location_name_to_id
        cls.item_name_groups = {"Everything": set(world_unlock_items.union(bonus_items).union(set("Nothing"))), "Slot Unlocks": world_unlock_items, "Bonus Slot Unlocks": bonus_items}
        cls.location_name_groups = {"Everywhere": set(world_unlock_locations.union(bonus_locations)), "Slot Rewards": world_unlock_locations, "Bonus Slot Rewards": bonus_locations}

        # update datapackage checksum
        worlds.network_data_package["games"][cls.game] = cls.get_data_package_data()
    def create_slotlock_item(self, slotName: str) -> LockItem:
        try:
            return LockItem(self,self.multiworld.world_name_lookup[slotName])
        except KeyError:
            return None
    def create_bonus_key(self, bonusSlot: int) -> Item:
        return Item(f"Unlock Bonus Slot {bonusSlot+1}", ItemClassification.progression,bonusSlot+1,self.player)
    def create_items(self) -> None:
        if hasattr(self.multiworld, "generation_is_fake"):
            # UT has no way to get the unlock items so just skip locking altogether
            return

        if self.options.slot_lock_list_mode.value == "whitelist":
            slots_to_lock = [slot for slot in self.options.slots_to_lock.value if any(slot == world.player_name for world in self.multiworld.worlds.values())]
        elif self.options.slot_lock_list_mode.value == "blacklist":
            slots_to_lock = [slot.player_name for slot in self.multiworld.worlds.values() if slot.player_name not in self.options.slots_to_lock.value and slot.player_name != self.player_name]
        else:
            # something went horribly wrong
            raise RuntimeError(f"[{self.player_name}] Invalid option for 'slot_lock_list_mode': {self.options.slot_lock_list_mode.value}")
        slots_to_lock = [slot for slot in slots_to_lock if slot in self.multiworld.world_name_lookup and self.multiworld.player_types[self.multiworld.world_name_lookup[slot]] == SlotType.player]
        slots_to_lock = sorted(slots_to_lock)
        if self.options.random_unlocked_slots.value > len(slots_to_lock):
            raise RuntimeError(f"[{self.player_name}] Too many random unlocked slots. Lock more slots, or reduce random_unlocked_slots")
        for i in range(self.options.random_unlocked_slots.value):
            slots_to_lock.remove(self.random.choice(slots_to_lock))

        # Conservative check if all slots are locked and there are no starting locations in SlotLock
        if len(slots_to_lock) >= len(list(filter(lambda s: self.multiworld.player_types[self.multiworld.world_name_lookup[s]] == SlotType.player,
                                                    self.multiworld.world_name_lookup))) - 1 and self.options.free_starting_items == 0 and self.options.free_unlocked_world_items == 0:
            raise RuntimeError(f"[{self.player_name}] No sphere 1 remaining in the multiworld. To fix this, either:\n* Set a slot as unlocked in slots_to_lock, \n* Set random_unlocked_slots to 1 or higher,\n* Set free_starting_items to true, or \n* Set free unlocked world items to 1 or higher.")
        logging.info(f"{self.player_name}: Locking {slots_to_lock}")
        self.slots_to_lock = slots_to_lock
        for world in self.options.associated_worlds:
            for associated_world in self.options.associated_worlds[world]:
                if world in slots_to_lock and associated_world in slots_to_lock:
                    self.associated_worlds.add(associated_world)
        #(creating regions in create_items to run always after create_regions for everything else.)
        self.region = Region("Menu",self.player,self.multiworld)
        def add_slot_item_to_option(option, world):
            slot = world.player_name
            if isinstance(option.value,dict) and (f"Unlock_{world.player}" in option.value.keys()):
                option.value[f"Unlock {slot}"] = option.value[f"Unlock_{world.player}"]
                del option.value[f"Unlock_{world.player}"]
            elif (isinstance(option.value,list) or isinstance(option.value,set)) and (f"Unlock_{world.player}" in option.value):
                option.value.add(f"Unlock {slot}")
                option.value.remove(f"Unlock_{world.player}")
        def remove_slot_item_from_option(option, world):
            if isinstance(option.value,dict) and (f"Unlock_{world}" in option.value.keys()):
                del option.value[f"Unlock_{world}"]
            elif (isinstance(option.value,list) or isinstance(option.value,set)) and (f"Unlock_{world}" in option.value):
                option.value.remove(f"Unlock_{world}")
        def add_slot_location_to_option(option, world):
            slot = world.player_name
            for i in range(10):
                if isinstance(option.value,dict) and (f"Lock_{world.player*10 + i}" in option.value.keys()):
                    option.value[f"Free Item {slot} {i+1}"] = option.value[f"Lock_{world.player*10 + i}"]
                    del option.value[f"Lock_{world.player*10 + i}"]
                elif (isinstance(option.value,list) or isinstance(option.value, set)) and (f"Lock_{world.player*10 + i}" in option.value):
                    option.value.add(f"Free Item {slot} {i+1}")
                    option.value.remove(f"Lock_{world.player*10 + i}")
        def remove_slot_location_from_option(option, world):
            for i in range(10):
                if isinstance(option.value,dict) and (f"Lock_{world*10 + i}" in option.value.keys()):
                    del option.value[f"Lock_{world*10 + i}"]
                elif (isinstance(option.value,list) or isinstance(option.value, set)) and (f"Lock_{world*10 + i}" in option.value):
                    option.value.remove(f"Lock_{world*10 + i}")
        for world in self.multiworld.worlds.values():
            if world.player_name in slots_to_lock:
                if isinstance(world, SlotLockWorld) and len(world.slots_to_lock) > 0:
                    raise Exception(f"Recursive slot lock: {self.player_name} locking {world.player_name} which locks other worlds, this is not allowed.")
                for i in range(min(10, self.options.unlock_item_copies.value + self.options.unlock_item_filler.value)):
                    self.region.add_locations({f"Free Item {world.player_name} {i+1}": self.location_name_to_id[f"Free Item {world.player_name} {i+1}"]}, LockLocation)
                    if i < self.options.unlock_item_copies.value and world.player_name not in self.associated_worlds:
                        self.multiworld.itempool.append(self.create_slotlock_item(world.player_name))
                    else:
                        self.multiworld.itempool.append(self.create_item("Nothing"))
                fixedLocations = []
                if world.player_name in self.options.associated_worlds.keys():
                    for associated_world in self.options.associated_worlds[world.player_name]:
                        if associated_world in self.associated_worlds:
                            location: Location = self.region.get_locations().pop()
                            location.place_locked_item(self.create_slotlock_item(associated_world))
                            index = -1
                            while self.multiworld.itempool[index].name != "Nothing":
                                index -= 1
                            self.multiworld.itempool.pop(index)
                            fixedLocations.append(location)
                        else:
                            logging.warning(f"{self.player_name} Warning: associated world {associated_world} not real world.")
                self.region.get_locations().extend(fixedLocations)

            else:
                try:
                    self.multiworld.push_precollected(self.create_slotlock_item(world.player_name))
                    for i in range(min(10, self.options.free_unlocked_world_items.value)):
                        self.multiworld.itempool.append(self.create_item("Nothing"))
                        self.region.add_locations({f"Free Item {world.player_name} {i+1}": self.location_name_to_id[f"Free Item {world.player_name} {i+1}"]}, LockLocation)
                except AttributeError:
                    pass

            class FakeOption:
                def __init__(self, value):
                    self.value = value
            if self.multiworld.player_types[world.player] == SlotType.player:
                add_slot_location_to_option(self.options.exclude_locations, world)
                add_slot_location_to_option(self.options.priority_locations, world)
                add_slot_location_to_option(self.options.start_location_hints, world)
                add_slot_item_to_option(self.options.local_items, world)
                add_slot_item_to_option(self.options.non_local_items, world)
                add_slot_item_to_option(self.options.start_hints, world)
                add_slot_item_to_option(self.options.start_inventory, world)
                for plando_block in self.options.plando_items:
                    add_slot_item_to_option(FakeOption(plando_block.items), world)
                    add_slot_location_to_option(FakeOption(plando_block.locations), world)
        for world in range(5001):
            remove_slot_location_from_option(self.options.exclude_locations, world)
            remove_slot_location_from_option(self.options.priority_locations, world)
            remove_slot_location_from_option(self.options.start_location_hints, world)
            remove_slot_item_from_option(self.options.local_items, world)
            remove_slot_item_from_option(self.options.non_local_items, world)
            remove_slot_item_from_option(self.options.start_hints, world)
            remove_slot_item_from_option(self.options.start_inventory, world)
            for plando_block in self.options.plando_items:
                remove_slot_item_from_option(FakeOption(plando_block.items), world)
                remove_slot_location_from_option(FakeOption(plando_block.locations), world)
        self.multiworld.regions.append(self.region)
        for bonusSlot in range(self.options.bonus_item_slots.value):
            bonusSlotRegion = Region(f"Bonus Slot {bonusSlot+1}", self.player, self.multiworld)
            for bonusDupes in range(min(self.options.bonus_item_copies.value + self.options.bonus_item_filler.value, 10)):
                if bonusDupes < self.options.bonus_item_copies.value:
                    self.multiworld.itempool.append(self.create_bonus_key(bonusSlot))
                else:
                    self.multiworld.itempool.append(self.create_item("Nothing"))
                locName = f"Bonus Slot {bonusSlot+1}{" " + str(bonusDupes+1) if bonusDupes > 0 else ""}"
                bonusSlotRegion.add_locations({locName: self.location_name_to_id[locName]})
            self.multiworld.regions.append(bonusSlotRegion)
            def rule(state: CollectionState, bonusSlot=bonusSlot):
                return state.has(f"Unlock Bonus Slot {bonusSlot+1}", self.player)
            self.region.connect(bonusSlotRegion,None, rule)

    def create_regions(self) -> None:
        pass
    def get_filler_item_name(self) -> str:
        return "Nothing"
    @classmethod
    def stage_pre_fill(cls, multiworld):
        for self in multiworld.get_game_worlds(cls.game): #workaround this being a classmethod lol
            for world in multiworld.worlds.values():
                if world.player_name in self.slots_to_lock:
                    currentOriginName = world.origin_region_name
                    currentOrigin: Region
                    currentOrigin = world.get_region(currentOriginName)
                    #region = Region(f"Lock {self.player}", world.player, self.multiworld)
                    #region.connect(currentOrigin,None,rule)
                    #self.multiworld.regions.append(region)
                    for exit in currentOrigin.get_exits():
                        old_rule = exit.access_rule
                        def rule(state: CollectionState, self=self, world=world, old_rule=old_rule):
                            return state.has(f"Unlock {world.player_name}",self.player) and old_rule(state)
                        exit.access_rule = rule
                    for location in currentOrigin.get_locations():
                        old_rule = location.access_rule
                        def rule(state: CollectionState, self=self, world=world, old_rule=old_rule):
                            return state.has(f"Unlock {world.player_name}",self.player) and old_rule(state)
                        location.access_rule = rule
                    multiworld.early_items[world.player] = {}
                    multiworld.local_early_items[world.player] = {}
                    world.options.progression_balancing.value = 0
    def fill_hook(self,
                  progitempool: List["Item"],
                  usefulitempool: List["Item"],
                  filleritempool: List["Item"],
                  fill_locations: List["Location"]) -> None:

        unfilled_slot_locking_items = []
        for item in progitempool:
            if isinstance(item, LockItem):
                unfilled_slot_locking_items.append(item)
        slot_locking_items = unfilled_slot_locking_items.copy()
        for location in self.multiworld.get_filled_locations():
            if location.item is not None and isinstance(location.item, LockItem):
                slot_locking_items.append(location.item)
        self.slot_locking_items = list(filter(lambda i: i.player == self.player, slot_locking_items))
        if unfilled_slot_locking_items: # Only run this once.
            logging.info(f"SlotLock (World) Linear Fill Phase 1: Filling slot unlock items.")
            fillpool = unfilled_slot_locking_items.copy()
            for item in fillpool:
                progitempool.remove(item)
            fill_state = Fill.sweep_from_pool(self.multiworld.state, progitempool)
            Fill.fill_restrictive(self.multiworld, fill_state, fill_locations,fillpool, name=f"SlotLock Slot Unlocks")
        if self.options.linear_fill.value > 0:
            self.linear_fill(progitempool, fill_locations)
    def get_temp_spheres(self, other_item_pool):
        state = CollectionState(self.multiworld)
        for i in other_item_pool:
            state.collect(i, True)
        locations = set(self.multiworld.get_locations())
        filled_locations = set(self.multiworld.get_filled_locations())

        while locations:
            sphere: Set[Location] = set()

            for location in locations:
                if location.can_reach(state):
                    sphere.add(location)
            yield sphere
            if not sphere:
                if locations:
                    yield locations  # unreachable locations
                break

            for location in sphere:
                if location.item:
                    state.collect(location.item, True, location)
            locations -= sphere
    def linear_fill(self, progitems: List[Item], locations: List[Location]):
        spheres = list(self.get_temp_spheres(progitems))
        sphere_unlocks = {}
        for sphere in range(len(spheres)):
            logging.debug(f"Sphere {sphere} with {len(spheres[sphere])}")
            sphere_unlocks[sphere] = set()
            for loc in spheres[sphere]:
                if loc.item in self.slot_locking_items and not any(map(lambda sphere: sphere in sphere_unlocks and loc.item in sphere_unlocks[sphere], range(sphere))):
                    sphere_unlocks[sphere].add(loc.item)
                    logging.debug(f"{sphere}: {loc.name} ({self.multiworld.player_name[loc.player]}) has {loc.item.name}")
            if not sphere_unlocks[sphere]:
                sphere_unlocks.pop(sphere)
        self.sphere_unlocks = sphere_unlocks
        fillpool = []
        for sphere in reversed(sorted(sphere_unlocks.keys())):
            logging.info(f"{self.player_name} Linear Fill Phase 2: Filling sphere {sphere+1}")
            for unlock_item in sphere_unlocks[sphere]:
                fillpool += filter(lambda item,player=unlock_item.unlock_player: item.player == player, progitems)

            amount_of_items = floor((len(fillpool) * (self.options.linear_fill.value / 100)))
            logging.debug(f"with {amount_of_items} / {len(fillpool)}")
            thisfillpool = fillpool.copy()
            for i in thisfillpool:
                fillpool.remove(i)
                progitems.remove(i)
            self.random.shuffle(thisfillpool)
            for i in range(len(thisfillpool) - amount_of_items):
                popped = thisfillpool.pop()
                fillpool.append(popped)
                progitems.append(popped)
            filllocations = []
            for later_sphere in range(sphere+1, len(spheres)):
                filllocations += filter(lambda location: location.item is None, spheres[later_sphere])
            filllocations_priority = list(filter(lambda location: location.progress_type == LocationProgressType.PRIORITY, filllocations))
            for i in filllocations_priority:
                filllocations.remove(i)
                locations.remove(i)
            for i in filllocations:
                locations.remove(i)
            priority_items = list(filter(lambda item: not item.deprioritized, thisfillpool))
            for i in priority_items:
                thisfillpool.remove(i)
            self.random.shuffle(filllocations_priority)
            fill_state = Fill.sweep_from_pool(self.multiworld.state, progitems + fillpool + thisfillpool)
            Fill.fill_restrictive(self.multiworld, fill_state, filllocations_priority, priority_items,
                                  name=f"{self.player_name} Linear Fill Sphere {sphere+1} Priority", allow_partial=True)
            thisfillpool += priority_items
            self.random.shuffle(thisfillpool)
            filllocations += filllocations_priority
            self.random.shuffle(filllocations)
            fill_state = Fill.sweep_from_pool(self.multiworld.state, progitems + fillpool)
            Fill.fill_restrictive(self.multiworld, fill_state, filllocations, thisfillpool,
                                  name=f"{self.player_name} Linear Fill Sphere {sphere+1}")
            locations += filllocations
            self.random.shuffle(locations)
            progitems += thisfillpool
            self.random.shuffle(progitems)
            fillpool += thisfillpool
            self.random.shuffle(fillpool)


    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has_all([f"Unlock {i}" for i in self.slots_to_lock] + [f"Unlock Bonus Slot {i+1}" for i in range(self.options.bonus_item_slots.value)], self.player)
        if not self.options.free_starting_items.value:
            for slot in self.slots_to_lock:
                for i in range(min(self.options.unlock_item_copies+self.options.unlock_item_filler,10)):
                    def rule(state: CollectionState, slot=slot):
                        return state.has(f"Unlock {slot}", self.player)
                    self.get_location(f"Free Item {slot} {i+1}").access_rule = rule
    def fill_slot_data(self):
        item_locations : Dict[str, list[tuple[int, int]]] = {}
        for item in self.multiworld.get_items():
            if item.player == self.player:
                item_locations[item.name] = list(map(lambda loc: (loc.player, loc.address),self.multiworld.find_item_locations(item.name, self.player, True)))
        return {
            "free_starting_items": self.options.free_starting_items.value,
            "auto_hint_locked_items": self.options.auto_hint_locked_items.value,
            "locked_slots": self.slots_to_lock,
            "unlock_item_copies": self.options.unlock_item_copies.value,
            "unlock_item_filler": min(10- self.options.unlock_item_copies.value, self.options.unlock_item_filler.value),
            "bonus_item_copies": self.options.bonus_item_copies.value,
            "bonus_item_filler": min(10- self.options.bonus_item_copies.value, self.options.bonus_item_filler.value),
            "bonus_item_slots": self.options.bonus_item_slots.value,
            "item_locations": item_locations
        }
    def post_fill(self) -> None:
        pass
    def collect(self,state: CollectionState, item: Item):
        res = super().collect(state,item)
        if res and "Unlock " in item.name and item.name.split("Unlock ")[1] in self.slots_to_lock:
            player_name = item.name.split("Unlock ")[1]
            for world in self.multiworld.worlds:
                if self.multiworld.worlds[world].player_name == player_name:
                    state.update_reachable_regions(world)
        return res
    def remove(self,state: CollectionState, item: Item):
        res = super().remove(state,item)
        if res and "Unlock " in item.name and item.name.split("Unlock ")[1] in self.slots_to_lock:
            player_name = item.name.split("Unlock ")[1]
            for world in self.multiworld.worlds:
                if self.multiworld.worlds[world].player_name == player_name:
                    state.update_reachable_regions(world)
        return res
    def modify_multidata(self, multidata: Dict[str, Any]):
        if len(self.slots_to_lock) == 0:
            return
        def hintfn(hint: Hint) -> Hint:
            if hasattr(hint, "status") and self.multiworld.player_name[hint.receiving_player] in self.slots_to_lock:
                from NetUtils import HintStatus
                hint = hint.re_prioritize(None, HintStatus.HINT_UNSPECIFIED)
            return hint
        for player in self.multiworld.player_ids:
            multidata["precollected_hints"][player] = set(map(hintfn, multidata["precollected_hints"][player]))

    def extend_hint_information(self, hint_data: Dict[int, Dict[int, str]]):
        """
        Fill in additional entrance information text into locations, which is displayed when hinted.
        structure is {player_id: {location_id: text}} You will need to insert your own player_id.
        """
        data = {}
        if self.options.auto_hint_locked_items.value > 0:
            for location in self.get_locations():
                data[location.address] = str(self.multiworld.find_item_locations(self.item_id_to_name[location.address // 10],self.player, True)).removeprefix("[").removesuffix("]")
        hint_data[self.player] = data
    def write_spoiler_header(self, spoiler_handle: TextIO) -> None:
        if self.sphere_unlocks:
            spoiler_handle.writelines(["\n", "Slotlock Spheres:\n"])
            spoiler_handle.writelines(list(map(lambda l: l+ "\n", map(str, self.sphere_unlocks.items()))))
