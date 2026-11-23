(disclaimer: this guide is not finished. other sections will be added soon.)
# Slotlock Guide: How it works, and what it does.
Slotlock is a metagame tool created by Sandra with the with the sole purpose of locking slots for archipelago multiworlds. 
Its as simple as that! It locks slots, and requires players to collect slot unlock items for slots to be logically available!
Q&A:
- When i play with SlotLock, why can i still play a locked slot? 
SlotLock is what is know as an honour system. What this means is that it relies on YOU to not invalidate it, which means not playing a slot before it's slot unlock item has been obtained. This is as close as we can get to truly locking slots.
- How do i lock all slots except for one/ones i have listed?
To achieve this, your yaml must have slot_whitelist set to false, and then either set random_unlocked_slots to 1, or put the name of the slot you want to have unlocked in the Slot_whitelist.
- My generation is taking really long, what happened?
A quirk of Slotlock is that it tends to really tank generation, causing it to take way longer than it would normally to get a successful seed. To remedy this, we either recommend running multiple generations using the Generate until Successful tool or the .bat file in the pins of the Slotlock thread, or increasing the starting slots/slot unlock copies. These allow for generations to just run without manual input, even if the generation fails, the tools will just restart the generation. Additionally, progression balancing may also affect generation negatively, so make sure to disable it on all slots if you think its needed.
- I'm getting slot unlocks too often, how do i remedy this? 
To stop this from happening, you have to change the amount of slot_unlock_copies to a lower amount. While it does help generation run quicker, don't forget that changing the starting_unlocked_slots also helps.
- How do i know what slots unlocked after starting the server?
Open the Slotlock client (using the archipelago launcher), and log into the server before using the /unlocked_slots command. 
- Slotlock has checks, but how do i send them out?
These checks are obtainable after collecting a slot unlock, and are sent by just having the Slotlock client open.  
- I'm recieving progression items from unlocking slots, how do i stop this from happening?
To do this, you need to put "Slot Rewards" into the "Excluded Locations" section of your yaml (at the very bottom).