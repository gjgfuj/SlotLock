from dataclasses import dataclass
from typing import Any, Dict
from BaseClasses import CollectionState, Item, ItemClassification, Location, MultiWorld, Region
from Options import OptionSet, PerGameCommonOptions, Range, StartInventoryPool, Toggle
import worlds
from worlds import AutoWorld
from worlds.generic import GenericWorld
from worlds.LauncherComponents import Component, components, icon_paths, launch_subprocess, Type
from NetUtils import Hint

def launch_client(*args):
    from .Client import launch
    from CommonClient import gui_enabled
    if not gui_enabled:
        print(args)
        launch(args)
    launch_subprocess(launch, name="SlotLockClient", args=args)
components.append(Component("Slot Lock Client", "SlotLockClient", func=launch_client,
                            component_type=Type.CLIENT, supports_uri=True, game_name="SlotLock"))

class LockItem(Item):
    coin_suffix = ""
    def __init__(self, world: "SlotLockWorld", player: int):
        Item.__init__(self,f"Unlock {world.multiworld.worlds[player].player_name}",ItemClassification.progression,player+1000,world.player)
class LockLocation(Location):
    pass

class SlotsToLock(OptionSet):
    """A list of slot player names to add a lock item to"""
    pass
class NumberOfUnlocks(Range):
    """Number of copies of each unlock item to include."""
    default = 1
    range_start = 1
    range_end = 10
class SlotsToLockWhitelistOption(Toggle):
    """If the list of slots to lock should be treated as a blacklist rather than a whitelist. If true, will lock every slot listed. If false, will lock every slot except this one and any slot listed."""
    default = 1
    pass
class FreeStartingItems(Toggle):
    """If true, the free items should be sent out immediately, or if false the 'Unlock {slot_name}' item will be required. If false, it will require other worlds to be open in sphere 1 instead else there will be no worlds available."""
    default = 1
    pass
class BonusItemSlots(Range):
    """Number of bonus item slots to include. These will be automatically unlocked when sent their individual keys."""
    default = 0
    range_start = 0
    range_end = 1000
class BonusItemDupes(Range):
    """Number of bonus items *per* item slot. This will also add this many keys for said slots into the pool."""
    default = 1
    range_start = 1
    range_end = 10
class RandomUnlockedSlots(Range):
    """Number of slots to randomly start with, from the slots that are locked."""
    default = 0
    range_start = 0
    range_end = 100
class AutoHintLockedItems(Toggle):
    """Whether the slotlock client should automatically ask for a hint (as long as it has enough hint points) when one of its items are hinted. Does not include items in locked worlds, only locations belonging to slotlock itself."""
    default = 0


@dataclass
class SlotLockOptions(PerGameCommonOptions):
    slots_to_lock: SlotsToLock
    slots_whitelist: SlotsToLockWhitelistOption
    number_of_unlocks: NumberOfUnlocks
    bonus_item_slots: BonusItemSlots
    bonus_item_dupes: BonusItemDupes
    free_starting_items: FreeStartingItems
    random_unlocked_slots: RandomUnlockedSlots
    auto_hint_locked_items: AutoHintLockedItems


class SlotLockWorld(AutoWorld.World):
    """Locks other player slots."""

    game = "SlotLock"
    options: SlotLockOptions
    options_dataclass = SlotLockOptions
    location_name_to_id = {f"Lock_{num}": num + 10000 for num in range(50000)}
    
    item_name_to_id = {f"Unlock_{num}": num + 10000 for num in range(50000)}
    slots_to_lock = []
    for i in range(1000):
            item_name_to_id[f"Unlock Bonus Slot {i+1}"] = i
            for j in range(10):
                location_name_to_id[f"Bonus Slot {i+1}{" " + str(j+1) if j > 0 else ""}"] = i*10 + j
    @classmethod
    def stage_generate_early(cls, multiworld: "MultiWorld"):
        item_name_to_id = {}
        location_name_to_id = {}
        for id, world in multiworld.worlds.items():
            item_name_to_id[f"Unlock {world.player_name}"] = id + 1000
            for i in range(10):
                location_name_to_id[f"Free Item {world.player_name} {i+1}"] = id*10 + i + 10000
        id = max(multiworld.worlds.keys())
        for i in range(1000):
            item_name_to_id[f"Unlock Bonus Slot {i+1}"] = i
            for j in range(10):
                location_name_to_id[f"Bonus Slot {i+1}{" " + str(j+1) if j > 0 else ""}"] = i*10 + j
        cls.item_name_to_id = item_name_to_id
        cls.location_name_to_id = location_name_to_id

        # update datapackage checksum
        worlds.network_data_package["games"][cls.game] = cls.get_data_package_data()
    def create_slotlock_item(self, slotName: str) -> LockItem:
        return LockItem(self,self.multiworld.world_name_lookup[slotName])
    def create_bonus_key(self, bonusSlot: int) -> Item:
        return Item(f"Unlock Bonus Slot {bonusSlot+1}", ItemClassification.progression,bonusSlot,self.player)
    def create_items(self) -> None:
        if hasattr(self.multiworld, "generation_is_fake"):
            # UT has no way to get the unlock items so just skip locking altogether
            return

        #print(self.location_name_to_id)
        if self.options.slots_whitelist.value:
            slots_to_lock = [slot for slot in self.options.slots_to_lock.value if any(slot == world.player_name for world in self.multiworld.worlds.values())]
        else:
            slots_to_lock = [slot.player_name for slot in self.multiworld.worlds.values() if slot.player_name not in self.options.slots_to_lock.value and slot.player_name != self.player_name]
        if self.options.random_unlocked_slots.value > len(slots_to_lock):
            raise RuntimeError("Too many random unlocked slots.")
        for i in range(self.options.random_unlocked_slots.value):
            slots_to_lock.remove(self.random.choice(slots_to_lock))
        print(f"{self.player_name}: Locking {slots_to_lock}")
        self.slots_to_lock = slots_to_lock
        #(creating regions in create_items to run always after create_regions for everything else.)
        self.region = Region("Menu",self.player,self.multiworld)
        for world in self.multiworld.worlds.values():
            if world.player_name in slots_to_lock:
                for i in range(self.options.number_of_unlocks.value):
                    self.region.add_locations({f"Free Item {world.player_name} {i+1}": self.location_name_to_id[f"Free Item {world.player_name} {i+1}"]}, LockLocation)
                    self.multiworld.itempool.append(self.create_slotlock_item(world.player_name))
            else:
                self.multiworld.push_precollected(self.create_slotlock_item(world.player_name))
        self.multiworld.regions.append(self.region)
        for bonusSlot in range(self.options.bonus_item_slots.value):
            bonusSlotRegion = Region(f"Bonus Slot {bonusSlot+1}", self.player, self.multiworld)
            for bonusDupes in range(self.options.bonus_item_dupes.value):
                self.multiworld.itempool.append(self.create_bonus_key(bonusSlot))
                locName = f"Bonus Slot {bonusSlot+1}{" " + str(bonusDupes+1) if bonusDupes > 0 else ""}"
                bonusSlotRegion.add_locations({locName: self.location_name_to_id[locName]})
            self.multiworld.regions.append(bonusSlotRegion)
            def rule(state: CollectionState, bonusSlot=bonusSlot):
                return state.has(f"Unlock Bonus Slot {bonusSlot+1}", self.player)
            self.region.connect(bonusSlotRegion,None, rule)

        

    def create_regions(self) -> None:
        pass
    def get_filler_item_name(self) -> str:
        return "A Cool Filler Item (No Satisfaction Guaranteed)"
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
                        def rule(state: CollectionState, world=world, old_rule=old_rule):
                            if state.stale[self.player]:
                                state.stale[world.player]
                            #print(f"Lock Rule Called for {world.player}, value {state.has(f"Unlock_{world.player}",self.player)}")
                            return state.has(f"Unlock {world.player_name}",self.player) and old_rule(state)
                        exit.access_rule = rule
                    for location in currentOrigin.get_locations():
                        old_rule = location.access_rule
                        def rule(state: CollectionState, world=world, old_rule=old_rule):
                            if state.stale[self.player]:
                                state.stale[world.player]
                            #print(f"Lock Rule Called for {world.player}, value {state.has(f"Unlock_{world.player}",self.player)}")
                            return state.has(f"Unlock {world.player_name}",self.player) and old_rule(state)
                        location.access_rule = rule
                    multiworld.early_items[world.player] = {}
                    multiworld.local_early_items[world.player] = {}
                    world.options.progression_balancing.value = 0

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has_all([f"Unlock {i}" for i in self.multiworld.player_name.values()] + [f"Unlock Bonus Slot {i+1}" for i in range(self.options.bonus_item_slots.value)], self.player)
        if not self.options.free_starting_items.value:
            for slot in self.slots_to_lock:
                for i in range(self.options.number_of_unlocks):
                    def rule(state: CollectionState, slot=slot):
                        return state.has(f"Unlock {slot}", self.player)
                    self.get_location(f"Free Item {slot} {i+1}").access_rule = rule
    def fill_slot_data(self):
        return {
            "free_starting_items": self.options.free_starting_items.value,
            "auto_hint_locked_items": self.options.auto_hint_locked_items.value
        }
    def post_fill(self) -> None:
        pass
    def modify_multidata(self, multidata: Dict[str, Any]):
        pass
        #def hintfn(hint: Hint) -> Hint:
        #    if hasattr(hint, "status") and self.multiworld.player_name[hint.receiving_player] in self.slots_to_lock:
        #        from NetUtils import HintStatus
        #        hint = hint.re_prioritize(None, HintStatus.HINT_UNSPECIFIED)
        #    return hint
        #for player in self.multiworld.player_ids:
        #    multidata["precollected_hints"][player] = set(map(hintfn, multidata["precollected_hints"][player]))
