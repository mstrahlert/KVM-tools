#!/usr/bin/env python
#
# Magnus Strahlert @ 171206
#   Configurable backup-script via virt-backup
# Magnus Strahlert @ 180306
#   Method as global option
# Magnus Strahlert @ 180322
#   Added support for retention
# Magnus Strahlert @ 180326
#   Made path to configfile a runtime option
# Magnus Strahlert @ 180413
#   Support for daemonisation

import ConfigParser
from datetime import datetime
from datetime import timedelta
from glob import glob
from subprocess import PIPE, Popen
import getopt
import time
import sys
import os
import shutil
import fnmatch
import libvirt

def cmdline(command):
  process = Popen(args = command, stdout = PIPE, shell = True,
                  universal_newlines = True)
  return process.communicate()[0]

# Print function to get a timestamp infront of the string
def tprint(msg, logfile = False):
  print("%s: %s" % (datetime.today().ctime(), msg))

  if logfile != False:
    now = datetime.now()
    logfile = now.strftime(logfile)
    with open(logfile, "a") as log:
      log.write("%s: %s\n" % (datetime.today().ctime(), msg))

def parse_config():
  try:
    opts, remainder = getopt.getopt(sys.argv[1:], "c:")
  except getopt.GetoptError:
    print("Syntax: %s [ -c <configfile ]" % sys.argv[0])
    sys.exit(2)

  # Defaults
  ####################################
  configfile = "virt-backup.conf"
  ####################################

  for opt, arg in opts:
    if opt == '-c':
      configfile = arg
    else:
      assertFalse("unknown option \"%s\"" % opt)

  if os.path.exists(configfile) == False:
    print("Error: Configfile \"%s\" does not exist" % configfile)
    sys.exit(2)

  config = ConfigParser.RawConfigParser()
  config.read(configfile)

  clients = config.sections()
  clients.remove('global')

  backups = {}

  logfile = config.get("global", "logfile")
  api = config.get("global", "api")
  if api != "libvirt" and api != "virt-backup":
    tprint("Error: Unknown api", logfile)

  # Parse and check client specific configuration
  for f in clients:
    if config.has_option(f, "weekday"):
      weekday = config.get(f, "weekday").lower()[0:3]
    else:
      weekday = False
    if config.has_option(f, "time"):
      time = config.get(f, "time")
    else:
      time = config.get("global", "start_at")
    if config.has_option(f, "dom"):
      dom = config.get(f, "dom")
    else:
      dom = False

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
        tprint("Error: Unknown method given for %s" % f, logfile)
        continue
    else:
      method = config.get("global", "method")

    if config.has_option(f, "retention"):
      retention = int(config.get(f, "retention"))
    else:
      retention = int(config.get("global", "retention"))

    # Populate our dictionary of configurations per client
    backups[f] = { "priority" : priority,
                   "method" : method,
                   "retention" : retention,
                   "weekday" : weekday,
                   "time" : time,
                   "dom" : dom,
                   "last_backup" : datetime(1970, 1, 1),
                   "next_backup" : False }

  # Validate and check various global options
  if not config.has_option("global", "backup_prg") and api != "libvirt":
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
  if config.has_option("global", "shutdown_timeout"):
    shutdown_timeout = config.get("global", "shutdown_timeout")
  else:
    shutdown_timeout = "90"

  if api != "libvirt":
    backup_prg = config.get("global", "backup_prg")
  else:
    backup_prg = None
  backup_dir = config.get("global", "backup_dir")

  backup_command = ("%s --action=convert --snapsize=%s --backupdir=%s" %
                   (backup_prg, snapsize, backup_dir))
  backup_command += " --debug"
  if config.has_option("global", "compress"):
    backup_command += " --compress"

  global_config = { "delay" : delay,
                    "snapsize" : snapsize,
                    "backup_prg" : backup_prg,
                    "backup_dir" : backup_dir,
                    "backup_command" : backup_command,
                    "shutdown_timeout" : shutdown_timeout,
                    "logfile" : logfile,
                    "api" : api }

  return global_config, backups

def shutdown_vm(conn, vm, logfile, shutdown_timeout):
  dom = conn.lookupByName(vm)
  if dom.state()[0] == libvirt.VIR_DOMAIN_RUNNING:
    tprint("%s is running, shutting down" % vm, logfile)
    dom.shutdown()
    shutdown_counter = 0
    while (dom.state()[0] != libvirt.VIR_DOMAIN_SHUTOFF):
      if (shutdown_counter >= shutdown_timeout):
        tprint("Timed out waiting for %s to shutdown" % vm, logfile)
        return False

      shutdown_counter += 1
      time.sleep(1)
    tprint("%s has now shutdown" % vm, logfile)
    return True
  else:
    tprint("%s is not running, nothing to do" % vm, logfile)
    return False

def suspend_vm(conn, vm, logfile):
  dom = conn.lookupByName(vm)
  if dom.state()[0] == libvirt.VIR_DOMAIN_RUNNING:
    tprint("%s is running, suspending" % vm, logfile)
    dom.suspend()
    tprint("%s is now suspended" % vm, logfile)
    return True
  else:
    tprint("%s is not running, nothing to do" % vm, logfile)
    return False

def start_vm(conn, vm, logfile):
  dom = conn.lookupByName(vm)
  if dom.state()[0] == libvirt.VIR_DOMAIN_SHUTOFF:
    tprint("%s is shutoff, restarting" % vm, logfile)
    dom.create()
    tprint("%s started" % vm, logfile)
    return True
  else:
    tprint("%s is not in a shutdown state, nothing to do" % vm, logfile)
    return False

def resume_vm(conn, vm, logfile):
  dom = conn.lookupByName(vm)
  if dom.state()[0] == libvirt.VIR_DOMAIN_PAUSED:
    tprint("%s is suspended, resuming" % vm, logfile)
    dom.resume()
    tprint("%s is now resumed" % vm, logfile)
    return True
  else:
    tprint("%s is not suspended, nothing to do" % vm, logfile)
    return False

def save_xml(conn, vm, logfile, path):
  dom = conn.lookupByName(vm)
  with open(path, "w") as xml:
    xml.write(dom.XMLDesc())

# Return a tuple of all disks that the VM has
def get_disks(conn, vm):
  from xml.etree import ElementTree
  from collections import namedtuple

  dom = conn.lookupByName(vm)
  root = ElementTree.fromstring(dom.XMLDesc())

  disks = root.findall("./devices/disk[@device='disk']")

  drivers = [disk.find("driver").attrib for disk in disks]
  sources = [disk.find("source").attrib for disk in disks]
  targets = [disk.find("target").attrib for disk in disks]

  if len(drivers) != len(sources) != len(targets):
    return False

  disk_info = namedtuple('DiskInfo', ['device', 'file', 'format'])
  disks_info = []
  for i in range(len(sources)):
    disks_info.append(disk_info(targets[i]["dev"], sources[i]["file"], drivers[i]["type"]))
  return disks_info

def get_backing_file(file):
  # Find out the backing file of a snapshot
  disk_info = cmdline("qemu-img info --force-share %s" % file)
  for line in disk_info.splitlines():
    key, value = line.split(": ")
    if key == "backing file":
      return value

  return False

def libvirt_snapshot(conn, vm, logfile):
  disks = []
  # For every disk of the VM, create an external snapshot
  for disk in get_disks(conn, vm):
    tprint("Snapshotting %s" % disk.file, logfile)
    disks += ["--diskspec %s,snapshot=external" % disk.device]
  os.system("virsh snapshot-create-as --domain %s --name %s "
            "--no-metadata --atomic --disk-only %s" %
            (vm, datetime.now().strftime("%F_%H-%M-%S"), " ".join(disks)))

def libvirt_backup(conn, vm, logfile, backup_dir):
  if not os.path.isdir("%s/%s" % (backup_dir, vm)):
    os.mkdir("%s/%s" % (backup_dir, vm))
  save_xml(conn, vm, logfile, "%s/%s/%s.xml" % (backup_dir, vm, vm))

  disks = []
  # Copy the backing qcow2 file(s) away as the backup, merge the
  # snapshots of all disks and then delete the snapshot itself.
  for disk in get_disks(conn, vm):
    inf = get_backing_file(disk.file)
    outf = "%s/%s/%s" % (backup_dir, vm, os.path.basename(inf))

    tprint("Copying %s" % inf, logfile)
    os.system("dd if=%s of=%s bs=4M iflag=direct oflag=direct "
              "conv=sparse" % (inf, outf))
    #shutil.copy2(get_backing_file(disk.file), "%s/%s" % (backup_dir, vm))
    os.system("virsh blockcommit %s %s --active --pivot" % (vm, disk.device))
    tprint("Removing snapshot %s" % disk.file, logfile)
    os.remove(disk.file)

def do_backup(global_config, backups, vms = None):
  # Loop through the clients sorted in order of priority
  for k, v in sorted(backups.items(), key=lambda item: (item[1]['priority'],
                     item[0])):
    # If true this is run in daemon mode and should backup all
    if vms == None:
      # First check if now is a good time to run backup for this client
      now = datetime.now()

      if (v['weekday'] != False and now.strftime('%A').lower()[0:3] not in
          v['weekday'].split(",")):
        # Wrong weekday
        continue
      if (v['dom'] != False and int(now.strftime('%-d')) not in
          map(int, v['dom'].split(","))):
        # Wrong day of month
        continue

      # Check if we have done a prior backup. If not, work out when it's due
      if v['next_backup'] == False:
        next_backup = datetime(now.year, now.month, now.day,
                               int(v['time'][0:2]), int(v['time'][2:4]))
        # Find out if the backup window has passed already for today
        now_mins = now.hour * 60 + now.minute
        next_mins = int(v['time'][0:2]) * 60 + int(v['time'][2:4])
        if (now_mins > next_mins):
          # The initial backup windows has passed, do the backup the next day
          next_backup += timedelta(1)

        backups[k]['next_backup'] = next_backup
      else:
        next_backup = v['next_backup']

      if now < next_backup:
        # Still not time to do the backup
        continue
      else:
        # The time has come to do the backup. Set the next scheduled
        # backup at the given time for the backup a day from now.
        backups[k]['next_backup'] = (datetime(now.year, now.month, now.day,
                                              int(v['time'][0:2]),
                                              int(v['time'][2:4])) +
                                     timedelta(1))
    # vms have been specified on command line. Turn on manual mode for
    # existing vms
    elif k not in vms:
      continue

    # Then handle retention
    if os.path.isdir("%s/%s" % (global_config['backup_dir'], k)):
      matches = sorted(fnmatch.filter(os.listdir("%s/%s" %
                       (global_config['backup_dir'], k)),
                       "[0-9]*-[0-9]*-[0-9]*_[0-9]*-[0-9]*-[0-9]*"))
      # As long as there are more than set number of backups, remove the
      # oldest. Since this will create an additional set (the backup that
      # this run will create), we need to check for greater or equality.
      # Thus we will momentarily while this run be one under the set
      # retention.
      while len(matches) >= v['retention']:
        tprint("Removing %s/%s/%s due to retention" %
               (global_config['backup_dir'], k, matches[0]),
               global_config['logfile'])
        shutil.rmtree("%s/%s/%s" % (global_config['backup_dir'], k,
                                    matches[0]))
        matches.pop(0)

    # Then do the backup
    tprint("Running backup for %s" % k, global_config['logfile'])

    backups[k]['last_backup'] = datetime.now()
    conn = None
    if v['method'] == "shutdown":
      if global_config['api'] == "virt-backup":
        os.system("%s --vm=%s --shutdown --shutdown-timeout=%s" %
                  (global_config['backup_command'], k,
                   global_config['shutdown_timeout']))
      elif global_config['api'] == "libvirt":
        if not conn:
          conn = libvirt.open("qemu:///system")
        if shutdown_vm(conn, k, global_config['logfile'],
                       global_config['shutdown_timeout']):
          libvirt_snapshot(conn, k, global_config['logfile'])
          start_vm(conn, k, global_config['logfile'])
          libvirt_backup(conn, k, global_config['logfile'],
                         global_config['backup_dir'])
    elif v['method'] == "suspend":
      if global_config['api'] == "virt-backup":
        os.system("%s --vm=%s" % (global_config['backup_command'], k))
      elif global_config['api'] == "libvirt":
        if not conn:
          conn = libvirt.open("qemu:///system")
        if suspend_vm(conn, k, global_config['logfile']):
          libvirt_snapshot(conn, k, global_config['logfile'])
          resume_vm(conn, k, global_config['logfile'])
          libvirt_backup(conn, k, global_config['logfile'],
                         global_config['backup_dir'])

    # Move the resulting xml and qcow2 file(s) to retention dir
    src_dir = "%s/%s" % (global_config['backup_dir'], k)
    dest_dir = "%s/%s/%s" % (global_config['backup_dir'], k,
                             datetime.now().strftime("%F_%H-%M-%S"))

    # Check if xml dumpfile exists. This is a status indicator.
    if os.path.exists("%s/%s.xml" % (src_dir, k)):
      os.mkdir(dest_dir)
      shutil.move("%s/%s.xml" % (src_dir, k), dest_dir)
      for vmdisk in glob("%s/*.qcow2" % src_dir):
        shutil.move("%s" % vmdisk, dest_dir)

      # Next scheduled backup only exists when running in daemon mode
      if vms == None:
        tprint("Backup finished for %s. Scheduling next for %s" % (k,
               backups[k]['next_backup'].ctime()), global_config['logfile'])
      else:
        tprint("Backup finished for %s." % k, global_config['logfile'])
    else:
      tprint("Backup failed for %s. Cannot find an xml dumpfile" % k,
             global_config['logfile'])

    time.sleep(int(global_config['delay']))

  return backups

def main():
  #conffile = read_config()
  #global_config, backup = parse_config(conffile)
  global_config, backups = parse_config()

  # Allow for manual backups of specified vms on command line
  if len(sys.argv) > 1:
    backups = do_backup(global_config, backups, sys.argv[1:])
  else:
    while (True):
      # Feed the variables back into the function, avoiding global variables
      # The content of 'backups' can change whereas 'global_config' cannot
      backups = do_backup(global_config, backups)
      time.sleep(60)

if __name__ == "__main__":
  main()
