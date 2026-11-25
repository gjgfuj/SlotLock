# Slotlock Guide: How it works, and what it does.

(Disclaimer: This guide is not finished. Other sections will be added soon.)

SlotLock is a metagame apworld created by Sandra with the sole purpose of locking slots for Archipelago MultiWorlds.
Its as simple as that! It locks slots, and requires players to collect slot unlock items for slots to be logically available!

## Q&A

### When I play with SlotLock, why can I still play a locked slot?

SlotLock works on what is known as an honour system. What this means is that it relies on YOU to not invalidate it, which means not playing a slot before it's slot unlock item has been obtained. This is as close as we can get to truly locking slots, without replacing the archipelago server..

### How do I lock all slots except for one/ones I have listed?

To achieve this, your yaml must have `slots_whitelist` set to `false`, and then either set `random_unlocked_slots` to `1`, or put the name of the slot you want to have unlocked in the `slots_to_lock` field, as setting `slots_whitelist` to `false` will cause it to lock everything else.

### My generation is taking really long, whats happening?

A quirk of SlotLock is that it tends to create a very restrictive generation, causing it to take way longer than it would normally to get a successful seed, along with creating possible errors in generation. To remedy this, we either recommend running multiple generations using the Generate until Successful tool or the .bat file in the pins of the Slotlock thread. These allow for generations to just run without manual input, even if the generation fails, the tools will just restart the generation. Additionally, turning off progression balancing can help, so make sure to disable it on all slots if you think its needed. Another option is increasing the starting slots/`unlock_item_copies` to ensure a larger sphere 1, or just choosing a starting game with a large sphere 1 to begin with.

### I'm getting slot unlocks too often, how do i remedy this?

To stop this from happening, you have to change the amount of `unlock_item_copies` to a lower amount. While it does help generation run quicker, don't forget that increasing the number of initially unlocked slots also helps.

### How do i know what slots are initially unlocked?

Open the SlotLock client (using the archipelago launcher), and log into the server to the SlotLock slot you created before using the /unlocked_slots command. Alternatively, you can check what slots are available by seeing what items the SlotLock slot has received.

### SlotLock has checks, but how do I send them out?

These checks are obtainable after collecting a slot unlock, and are sent by just having the SlotLock client open.

### I'm receiving progression items from unlocking slots, how do i stop this from happening?

To do this, you need to put `Slot Rewards` into the `excluded_locations` section of your yaml (at the very bottom).

# YAML Guide:

This section of the guide will cover the parts of the yaml that may seem confusing at a first glance, like `Linear Fill` or Associated Worlds.

### Important Settings

The settings that will be listed here may not necessarily be important, but are settings we feel may need explanation as they can change how a slotlock generates beyond just adding a copy of an item. A full list of these important settings will be listed below.

- `slots_whitelist`: The slot whitelist whitelists (or blacklists) slots based on whether or not they are inserted into the `slots_to_lock` list above. Having this set to true will make it so any slot in the `slots_to_lock` list will be locked, and the slots not listed will stay unlocked. Having this set to false will instead do the opposite, with the slots listed in the `slots_to_lock` list instead being unlocked at the start of a game, and the slots not listed will be locked. This setting works in tandem with the `random_unlocked_slots` setting. (Explanation in that section.)
- `linear_fill`: Whilst linear fill on the surface seems complicated, it can be explained very easily. What linear fill does is only make progression items collectable for slots the sphere AFTER they have been unlocked. For example, Slot 1 can have its items anywhere because its a starting game. However, Slot 2 can only have its items in places logically available after it is unlocked, because it was initially locked. The intention of linear fill is to make it so unlocking a game doesn't immediately have it go-mode because it's been locked for a long time.
- `associated_worlds`: Associated worlds is like plando. You list out a slot like this: `Slot1: [Slot2, Slot3, Slot4]`. What this will do will unlock Slot2, Slot3, and Slot4 when Slot 1 is unlocked, and its as simple as that. However as stated by Sandra, the intended use for this is to have a slot with all its items dedicated to another slot, e.g: A bingo where all the items given are for a Hollow Knight.
- `random_unlocked_slots`: This setting dictates how many slots are unlocked at the start of a multiworld. As mentioned before, it works in tandem with the `slots_whitelist`. If you have the `slots_whitelist` set to false and leave the `slots_to_lock` field empty, then have the `random_unlocked_slots` set to 1, only one slot out of all locked will be unlocked at the start of a multiworld.

### Bonus/Copy Settings

(Disclaimer: This next section is incredibly long and contains large amounts of math due to this not being easy to explain.)
These settings allow for Copies, or "Bonus", versions of items to be placed into the pool. This can do various things, like allow for more free items from collecting a slot unlock, or add more versions of each slot unlock into the pool. The best way to describe what these each do is with a formula. If you have `slots_whitelist` set to true, then locked_slot_count = slots_to_lock length. If `slots_whitelist` is set to false, then locked_slot_count = total_slots - slots_to_lock length. This allows us to figure out the math needed for other settings. slotlock_items = locked_slot_count _ unlock_item_copies + bonus_item_slots _ bonus_item_copies. The formula above tells us how many items slotlock contains based on each setting, so if all of the above is 4, then the slotlock_items would be 32. slotlock_locations = locked_slot_count _ (unlock_item_copies + unlock_item_filler) + bonus_item_slots _ (bonus_item_copies + bonus_item_filler). Once more, if we assume each variable in the formula above is 4, then the locations in slotlock will be 64. If we subtract 64 by 32, then we end up with 32, which is how many of those items are the `nothing` item.

### Misc Settings

The settings that will be listed here are settings that don't fit into the "copy" category, but aren't important enough to fit into the "important" category. Below is the list of said settings.

- `free_starting_items`: If this setting is set to true, then all items that would be sent by unlocking worlds will instead be given out at the very start of the multiworld instead.
- `free_unlocked_world_items`: Based on what this is set to, there will be that amount of items for each slot when it is unlocked, or when using the setting mentioned previously. For example, setting this to 10 will reward you with 10 items everytime you unlock a slot.
- `auto_hint_locked_items`: What this setting does is that when you next hint something in a locked world (excluding starting hints), the next time you open the slotlock client the next logical unlock for the slot the item is in get hinted.
