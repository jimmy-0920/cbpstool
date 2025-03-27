import sys
import logging
import requests
from datetime import datetime
from cbpsthttp import INSTANCE_HOST, TOKEN, HEADERS, GROUP_SETTINGS # config for http requests
from cbpstconf import TARGET_GROUPS, DO_NOT_ADD, DO_NOT_REMOVE # config for automations (users ids, group ids)


'''
Clipboard Parent Sync Tool (cbpstool.py)
NGS
v1.0
'''


'''
README: Logging
Writes a log file to same directory as cbpstool.py on each run with date and time stamp in file name
Example: cbpstool_log_26-03-2025_15-04-50 (cbpstool_log_DAY-MONTH-YEAR_HOUR-MINUTE-SECOND)
'''


LOG_FILE_NAME = f"cbpstool_log_{datetime.now().strftime("%d-%m-%Y_%H-%M-%S.log")}"
logging.basicConfig(filename=LOG_FILE_NAME, encoding='utf-8', level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s", datefmt="%d-%m-%Y_%H-%M-%S")


def main():
    '''
    README: Main Loop Explained
    Loop over all Schoolbox Group IDs listed in TARGET_GROUPS
    Skip Group if there are no members found within group
    Define 2 lists (below) to save Schoolbox User IDs. These lists are cleared on each loop
    1. GROUP_PARENTS: Schoolbox ID of all parents CURRENTLY in the group
    2. LINKED_PARENTS: Schoolbox ID of all parents linked to a STUDENT currently in the group
    Schoolbox IDs are used to determine:
    -if a parent should be added to a group
    -if a parent should be removed from a group
    -if a parent should NOT be removed from a group (defined in DO_NOT_REMOVE)
    -if a parent should NOT be added to a group (defined in DO_NOT_ADD)
    *thisGroup = the current Schoolbox group ID
    *thisGroupName = the Schoolbox group label defined in cbpstoolconf.py
    '''
    
    # Exit script if there is no group ids found in TARGET_GROUPS
    if not TARGET_GROUPS:
        logging.warning("No Group IDs Found in TARGET_GROUPS; Exiting...")
        sys.exit()

    logging.info(f"(START): Processing {len(TARGET_GROUPS)} Groups: {TARGET_GROUPS}")

    # Save schoolbox user ids in GROUP_PARENTS and LINKED_PARENTS
    for thisGroup, thisGroupName in TARGET_GROUPS.items():

        GROUP_PARENTS = [] # Parent schoolbox ids found in thisGroup
        LINKED_PARENTS = [] # Parent schoolbox ids linked to a student (guardian) found in thisGroup
        
        try:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): Attempting GET Request /group/getData/{thisGroup}")
            req = requests.request("GET", f"{INSTANCE_HOST}/group/getData/{thisGroup}", headers=HEADERS, timeout=10)
            req.raise_for_status()
        except requests.exceptions.HTTPError as error:
            logging.critical(f"EXITING! (HTTP Error) {error.args[0]}")
            sys.exit()
        except requests.exceptions.ConnectionError as error:
            logging.critical(f"EXITING! (Connection Error) {error.args[0]}")
            sys.exit()
        except requests.exceptions.ReadTimeout as error:
            logging.critical(f"EXITING! (Time Out Error) {error.args[0]}")
            sys.exit()
        except requests.exceptions.RequestException  as error:
            logging.critical(f"EXITING! (Unexpected Exception) {error.args[0]}")
            sys.exit()
        
        groupMembers = req.json()["members"] # Schoolbox parent ids already in thisGroup
      
        # Skip groups with no members. No users to process
        if not groupMembers:
            logging.error(f"(Group:{thisGroup}:{thisGroupName}): No Members Found. Skipping...")
            continue

        for member in groupMembers:
            # Populate with group parent id (parents already members of thisGroup)
            if member["role"] == "Current Parent":
                GROUP_PARENTS.append(member["id"])

            # Populate linked parents schoolbox ids (parents linked to students currently in thisGroup)
            if member["role"] == "Primary Student" or member["role"] == "Secondary Student" or member["role"] == "Kinder Students":
                try:
                    logging.info(f"(Group:{thisGroup}:{thisGroupName}): Attempting GET Request /api/user/{member['id']}")
                    linkedParents = requests.request("GET", f"{INSTANCE_HOST}/api/user/{member['id']}", headers=HEADERS, timeout=10)
                    req.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    logging.critical(f"EXITING! (HTTP Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ConnectionError as error:
                    logging.critical(f"EXITING! (Connection Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ReadTimeout as error:
                    logging.critical(f"EXITING! (Time Out Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.RequestException  as error:
                    logging.critical(f"EXITING! (Unexpected Exception) {error.args[0]}")
                    sys.exit()
                    
                # Account for the usual case where there is more than 1 parent (guardian) linked to a student
                for user in linkedParents.json()["guardians"]:
                    LINKED_PARENTS.append(user["id"])

        
        #logging.info(f"(Group:{thisGroup}:{thisGroupName}): Processing...")
        #logging.info(f"Group Parents: {GROUP_PARENTS}")
        #logging.info(f"Linked Parents: {LINKED_PARENTS}")
    
        '''
        README: Add/Remove Parent Group Membership Logic
        -If a parent in thisGroup is NOT linked to a student, they are removed
        -If a parent is NOT in thisGroup AND they are linked to a student in thisGroup, they are added
        *If a parent is found in DO_NOT_ADD, they are not added to any group
        *If a parent is found in DO_NOT_REMOVE, they are added to groups but never removed
        '''
        
        # Reset stat counters before processing each group
        groupChangedCount = 0
        groupDoNotAdd = 0
        groupNotRemovedCount = 0
        groupAdded = 0
        groupRemoved = 0
    
        '''
        ADD thisParent to thisGroup IF:
        -Condition 1: Parent not in DO_NOT_ADD
        -Condition 2: Parent not currently in thisGroup
        '''
        for thisParent in LINKED_PARENTS:
            if thisParent in DO_NOT_ADD:
                '''
                Parent found in DO_NOT_ADD is never added to any group
                '''
                logging.info(f"(Group:{thisGroup}:{thisGroupName}): Do Not Add Parent {thisParent}; Found ID in DO_NOT_ADD")
                groupDoNotAdd += 1
                continue # Skip this Parent (Found ID in DO_NOT_ADD)
            if thisParent not in GROUP_PARENTS:
                '''
                Parent linked to a student but they are not in the group is added
                '''
                try:
                    logging.info(f"(Group:{thisGroup}:{thisGroupName}): Attempting POST Request /api/user/{thisParent}/group/{thisGroup}")
                    requests.request("POST", f"{INSTANCE_HOST}/api/user/{thisParent}/group/{thisGroup}", json=GROUP_SETTINGS, headers=HEADERS, timeout=10)
                    req.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    logging.critical(f"EXITING! (HTTP Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ConnectionError as error:
                    logging.critical(f"EXITING! (Connection Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ReadTimeout as error:
                    logging.critical(f"EXITING! (Time Out Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.RequestException  as error:
                    logging.critical(f"EXITING! (Unexpected Exception) {error.args[0]}")
                    sys.exit()
                        
                logging.info(f"(Group:{thisGroup}:{thisGroupName}): Added Parent {thisParent}; Linked to Student")
                groupChangedCount += 1
                groupAdded += 1
                
        '''
        REMOVE thisParent from thisGroup IF:
        -Condition 1: Parent not in DO_NOT_REMOVE
        -Condition 2: Parent not linked to any student currently in thisGroup
        '''
        for thisParent in GROUP_PARENTS:
            if thisParent in DO_NOT_REMOVE:
                '''
                Parent found in DO_NOT_REMOVE is never removed from ANY group
                '''
                logging.info(f"(Group:{thisGroup}:{thisGroupName}): Do Not Remove Parent {thisParent}; Found ID in DO_NOT_REMOVE")
                groupNotRemovedCount += 1
                continue # Skip this parent (Found ID in DO_NOT_REMOVE)
            if thisParent not in LINKED_PARENTS:
                '''
                A parent currently in thisGroup but with no students linked to them is removed
                '''
                try:
                    logging.info(f"(Group:{thisGroup}:{thisGroupName}): Attempting DELETE Request /api/user/{thisParent}/group/{thisGroup}")
                    requests.request("DELETE", f"{INSTANCE_HOST}/api/user/{thisParent}/group/{thisGroup}", headers=HEADERS, timeout=10)
                    req.raise_for_status()
                except requests.exceptions.HTTPError as error:
                    logging.critical(f"EXITING! (HTTP Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ConnectionError as error:
                    logging.critical(f"EXITING! (Connection Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.ReadTimeout as error:
                    logging.critical(f"EXITING! (Time Out Error) {error.args[0]}")
                    sys.exit()
                except requests.exceptions.RequestException  as error:
                    logging.critical(f"EXITING! (Unexpected Exception) {error.args[0]}")
                    sys.exit()
                
                logging.info(f"(Group:{thisGroup}:{thisGroupName}): Removed Parent {thisParent}; Not linked to any Student in Group and ID not found in DO_NOT_REMOVE")
                groupChangedCount += 1
                groupRemoved += 1
        
        '''
        Log stats for any updates made to groups
        Stats below for debugging. They can be removed to reduce log file clutter
        '''
        if groupChangedCount == 0:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): No Change!")
        if groupAdded >= 1:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): {groupAdded} Parent(s) Added")
        if groupRemoved >= 1:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): {groupRemoved} Parent(s) Removed")
        if groupDoNotAdd >= 1:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): {groupDoNotAdd} Parent(s) Not Added")
        if groupNotRemovedCount >= 1:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): {groupNotRemovedCount} Parent(s) Not Removed")
        if groupChangedCount >= 1:
            logging.info(f"(Group:{thisGroup}:{thisGroupName}): Total Changes: {groupChangedCount}")
            
    
    # Processing groups done! Write group summary to log file
    logging.info(f"(DONE): Finished Processing Groups: {TARGET_GROUPS}")
            
    
if __name__ == '__main__':
    main()
    