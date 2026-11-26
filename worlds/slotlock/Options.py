from dataclasses import dataclass

from Options import OptionSet, PerGameCommonOptions, Range, StartInventoryPool, Toggle, Choice, OptionDict, OptionGroup


class SlotsToLock(OptionSet):
    """A list of slot player names to add a lock item to."""
    pass
class NumberOfUnlocks(Range):
    """Number of copies of each unlock item to include."""
    default = 1
    range_start = 1
    range_end = 10
class UnlockItemFiller(Range):
    """Number of additional locations for the world unlock slots. This amount is capped to 10, and automatically includes any copies of the bonus item key plus the additional locations here. The additional locations each add a Nothing item to the pool."""
    default = 0
    range_start = 0
    range_end = 9
class SlotLockListMode(Choice):
    """Defines how the slots_to_lock list works.

    - **Whitelist**: the slots listed will get locked
                     the slots not listed will be open from the start
    - **Blacklist**: the slots listed will be open from the start
                     the slots not listed will get locked
    """
    option_whitelist = 0
    option_blacklist = 1
    default = option_whitelist
    pass
class FreeSlotItems(Toggle):
    """If true, the free items should be sent out immediately for locked worlds, or if false the 'Unlock {slot_name}' item will be required. If false, it will require other worlds to be open in sphere 1 instead else there will be no worlds available."""
    default = 0
    pass
class FreeUnlockedWorldItems(Range):
    """Adds filler and locations equal to this number, per starting slot of the world."""
    default = 0
    range_start = 0
    range_end = 10
class BonusItemSlots(Range):
    """Number of bonus item slots to include. These will be automatically unlocked when sent their individual keys."""
    default = 0
    range_start = 0
    range_end = 1000
class BonusItemDupes(Range):
    """Number of copies of bonus slot unlocks."""
    default = 1
    range_start = 1
    range_end = 10
class BonusItemFiller(Range):
    """Number of additional locations for the bonus item slots. This amount is capped to 10, and automatically includes any copies of the bonus item key plus the additional locations here."""
    default = 0
    range_start = 0
    range_end = 9
class RandomUnlockedSlots(Range):
    """Number of slots to randomly start with, from the slots that are locked."""
    default = 0
    range_start = 0
    range_end = 100
class AutoHintLockedItems(Toggle):
    """Whether the slotlock client should automatically scout locations in other worlds where its items are if one of its items are hinted."""
    default = 0
    option_no = 0
    option_yes = 1
    alias_true = 1
    alias_false = 0
class AssociatedWorlds(OptionDict):
    """Allows you to associate a list of worlds with another world. These worlds slot unlocks will then be unlocked at the same time as the primary world. Format `WorldName: [AssociatedWorld1,AssociatedWorld2]`. The maximum number of associated worlds per world is 10, and will cause the associated world to only have 1 copy of its world."""
    pass
class LinearFill(Range):
    """If greater than 0, will attempt a linear fill where each locked world's items are only available in spheres after that world is unlocked, for x% of each world's progression items. (EXPERIMENTAL)"""
    default = 0
    range_start = 0
    range_end = 100
    option_none = 0
    option_full = 100
    alias_no = 0
    alias_yes = 100
    alias_true = 100
    alias_false = 0
@dataclass
class SlotLockOptions(PerGameCommonOptions):
    slots_to_lock: SlotsToLock
    slot_lock_list_mode: SlotLockListMode
    unlock_item_copies: NumberOfUnlocks
    unlock_item_filler: UnlockItemFiller
    bonus_item_slots: BonusItemSlots
    bonus_item_copies: BonusItemDupes
    bonus_item_filler: BonusItemFiller
    free_starting_items: FreeSlotItems
    free_unlocked_world_items: FreeUnlockedWorldItems
    random_unlocked_slots: RandomUnlockedSlots
    auto_hint_locked_items: AutoHintLockedItems
    associated_worlds: AssociatedWorlds
    linear_fill: LinearFill

option_groups = [
    OptionGroup("Slot Unlock Options", [
        NumberOfUnlocks,
        UnlockItemFiller,
        FreeUnlockedWorldItems,
    ]),
    OptionGroup("Bonus Slot Options", [
        BonusItemSlots,
        BonusItemDupes,
        BonusItemFiller
    ]),
    OptionGroup("Start Options", [
        FreeSlotItems,
        RandomUnlockedSlots
    ]),
    OptionGroup("Other Options", [
        AutoHintLockedItems,
        AssociatedWorlds,
        LinearFill
    ])
]
