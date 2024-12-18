from dataclasses import dataclass
from typing import Any, Dict
from BaseClasses import CollectionState, Item, ItemClassification, Location, MultiWorld, Region
from Options import OptionSet, PerGameCommonOptions, Range, StartInventoryPool, Toggle
import worlds
from worlds import AutoWorld
from worlds.generic import GenericWorld
from worlds.LauncherComponents import Component, components, icon_paths, launch_subprocess, Type

def launch_client(*args):
    from .Client import launch
    launch_subprocess(launch, name="SlotLockClient", args=args)
components.append(Component("Slot Lock Client", "SlotLockClient", func=launch_client,
                            component_type=Type.CLIENT))

class LockItem(Item):
    coin_suffix = ""
    def __init__(self, world: "SlotLockWorld", player: int):
        Item.__init__(self,f"Unlock {world.multiworld.worlds[player].player_name}",ItemClassification.progression,player,world.player)
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


@dataclass
class SlotLockOptions(PerGameCommonOptions):
    slots_to_lock: SlotsToLock
    slots_whitelist: SlotsToLockWhitelistOption
    number_of_unlocks: NumberOfUnlocks
    start_inventory_from_pool: StartInventoryPool


class SlotLockWorld(AutoWorld.World):
    """Locks other player slots."""

    game = "SlotLock"
    options: SlotLockOptions
    options_dataclass = SlotLockOptions
    location_name_to_id = {f"Lock_{num}": num for num in range(2000)}
    
    item_name_to_id = {f"Unlock_{num}": num for num in range(2000)}
    def stage_generate_early(multiworld: "MultiWorld"): # type: ignore
        cls = SlotLockWorld
        item_name_to_id = {}
        location_name_to_id = {}
        for id, world in multiworld.worlds.items():
            item_name_to_id[f"Unlock {world.player_name}"] = id
            for i in range(10):
                location_name_to_id[f"Free Item {world.player_name} {i+1}"] = id*10 + i

        cls.item_name_to_id = item_name_to_id
        cls.location_name_to_id = location_name_to_id

        # update datapackage checksum
        worlds.network_data_package["games"][cls.game] = cls.get_data_package_data()
    def create_item(self, slotName: str) -> LockItem:
        return LockItem(self,self.multiworld.world_name_lookup[slotName])

    def create_items(self) -> None:

        if hasattr(self.multiworld, "generation_is_fake"):
            # UT has no way to get the unlock items so just skip locking altogether
            return
        if self.options.slots_whitelist.value:
            slots_to_lock = self.options.slots_to_lock.value
        else:
            slots_to_lock = [slot.player_name for slot in self.multiworld.worlds.values() if slot.player_name not in self.options.slots_to_lock.value and slot.player_name != self.player_name]
        #(creating regions in create_items to run always after create_regions for everything else.)
        for world in self.multiworld.worlds.values():
            if world.player_name in slots_to_lock:
                currentOriginName = world.origin_region_name
                world.origin_region_name = f"Lock {self.player}"
                currentOrigin = world.get_region(currentOriginName)
                region = Region(f"Lock {self.player}", world.player, self.multiworld)
                def rule(state: CollectionState, world=world):
                    if state.stale[self.player]:
                        state.stale[world.player]
                    #print(f"Lock Rule Called for {world.player}, value {state.has(f"Unlock_{world.player}",self.player)}")
                    return state.has(f"Unlock {world.player_name}",self.player)
                region.connect(currentOrigin,None,rule)
                self.multiworld.regions.append(region)
                world.options.progression_balancing.value = 0
        self.region = Region("Menu",self.player,self.multiworld)
        for world in self.multiworld.worlds.values():
            if world.player_name in slots_to_lock:
                for i in range(self.options.number_of_unlocks.value):
                    self.region.add_locations({f"Free Item {world.player_name} {i+1}": self.location_name_to_id[f"Free Item {world.player_name} {i+1}"]}, LockLocation)
                    self.multiworld.itempool.append(self.create_item(world.player_name))
            else:
                self.multiworld.push_precollected(self.create_item(world.player_name))
        self.multiworld.regions.append(self.region)
        

    def create_regions(self) -> None:
        pass

    def get_filler_item_name(self) -> str:
        return "A Cool Filler Item (No Satisfaction Guaranteed)"

    def set_rules(self) -> None:
        self.multiworld.completion_condition[self.player] = lambda state: state.has_all([f"Unlock {i}" for i in self.multiworld.player_name.values()], self.player)
 
    def post_fill(self) -> None:
        pass

