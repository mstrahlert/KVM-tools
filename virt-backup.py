#!/usr/bin/env python
#
# Magnus Strahlert @ 171206
#   Configurable backup-script via virt-backup
# Magnus Strahlert @ 180306
#   Method as global option
# Magnus Strahlert @ 180322
#   Added support for retention

import ConfigParser
from datetime import datetime
import time
import sys
import os
import shutil
import fnmatch

config = ConfigParser.RawConfigParser()
config.read('virt-backup.conf')

clients = config.sections()
clients.remove('global')

backups = {}

# Print function to get a timestamp infront of the string
def tprint(msg):
  print "%s: %s" % (datetime.today().ctime(), msg)

# Parse and check client specific configuration
for f in clients:
  if config.has_option(f, "weekday"):
    # If today isn't the day we're meant to backup, skip this one
    now = datetime.now()
    if now.strftime('%A').lower()[0:3] != config.get(f, "weekday").lower()[0:3]:
      tprint("Skipping %s due to wrong weekday" % f)
      continue

  # Set priority to given value between 1 and 99 (default if not entered)
  if config.has_option(f, "priority"):
    priority = int(config.get(f, "priority"))
    if priority > 99:
      priority = 99
    elif priority < 1:
      priority = 1
  else:
    priority = 99

  # Verify method. Default method is set by global config if not entered.
  if config.has_option(f, "method"):
    method = config.get(f, "method")
    if method != "suspend" and method != "shutdown":
      tprint("Error: Unknown method given for %s" % f)
      continue
  else:
    method = config.get("global", "method")

  if config.has_option(f, "retention"):
    retention = int(config.get(f, "retention"))
  else:
    retention = int(config.get("global", "retention"))
 
  # Populate our dictionary of configurations per client
  backups[f] = { "priority" : priority, "method" : method, "retention" : retention }

# Validate and check various global options
if not config.has_option("global", "backup_prg"):
  sys.exit("Missing required option backup_prg")
if not config.has_option("global", "backup_dir"):
  sys.exit("Missing required option backup_dir")
if config.has_option("global", "delay"):
  delay=config.get("global", "delay")
else:
  delay="30"
if config.has_option("global", "snapsize"):
  snapsize=config.get("global", "snapsize")
else:
  snapsize="100G"

backup_prg = config.get("global", "backup_prg")
backup_dir = config.get("global", "backup_dir")

backup_command = "%s --action=convert --snapsize=%s --debug" % (backup_prg, snapsize)
if config.has_option("global", "compress"):
  backup_command += " --compress"

# Loop through the clients sorted in order of priority
for k, v in sorted(backups.items(), key=lambda item: (item[1]['priority'], item[0])):
  # First handle retention
  if v['retention'] > 1:
    matches = sorted(fnmatch.filter(os.listdir("%s/%s" % (backup_dir, k)), "[0-9]*-[0-9]*-[0-9]*_[0-9]*-[0-9]*-[0-9]*"))
    # As long as there are more than set number of backups, remove the oldest
    while len(matches) > v['retention']:
      tprint("Removing %s/%s/%s due to retention" % (backup_dir, k, matches[0]))
      shutil.rmtree("%s/%s/%s" % (backup_dir, k, matches[0]))
      matches.pop(0)

  # Then do the backup
  tprint("Backing up %s" % k)
  backup_command += " --backupdir=%s/%s" % (backup_dir, datetime.now().strftime("%F_%H-%M-%S"))

  if v['method'] == "shutdown":
    if config.has_option("global", "shutdown_timeout"):
      shutdown_timeout = config.get("global", "shutdown_timeout")
    else:
      shutdown_timeout = "90"

    os.system("%s --vm=%s --shutdown --shutdown-timeout=%s" % (backup_command, k, shutdown_timeout))
  elif v['method'] == "suspend":
    os.system("%s --vm=%s" % (backup_command, k))

  time.sleep(int(delay))
