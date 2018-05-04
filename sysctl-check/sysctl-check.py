#!/usr/bin/python
import re
import subprocess
import sys
import os

def lines_to_dict(lines):
    dict = {}
    lines[:] = [s.strip() for s in lines if re.match(r'^\s*[^ #]+', s)]
    lines[:] = [re.sub(r'\s+', ' ', s) for s in lines]
    for line in lines:
        dict[line.split('=')[0].strip()] = line.split('=')[1].strip()
    return dict

def calculate_line_length(except_list, live_dict):
    key_len = 0
    value_len = 0
    combined = "|".join(except_list)

    for key in live_dict:
        if re.match(combined, key):
            continue
        if len(key) > key_len:
            key_len = len(key) + 1
        #max_key = key
        if len(live_dict[key]) > value_len:
            value_len = len(live_dict[key]) + 1
        #max_value = live_dict[key]
    #print max_key, max_value
    return key_len + value_len*3 + 2, key_len, value_len

def print_horizontal_line(n):
    print '=' * n, '\n'

def print_columns():
    print '%*s %*s %*s %*s\n' % (-key_len, 'KERNEL PARAMETER', -value_len, 'ORG VALUE', -value_len, 'CONF VALUE', -value_len, 'LIVE VALUE')

def verify_params(except_list, merge_dict, live_dict, key_len, value_len):
    diff_list = []
    live_load_list = []
    combined = "|".join(except_list) or "No Exception List"
    for key in live_dict:
        if re.match(combined, key):
            continue
        if key in merge_dict:
            if key not in org_dict:
                # only sysctl -p OR both p and w
                org_dict[key] = ""
                if merge_dict[key] != live_dict[key]:
                    diff_list.append(key)
            else:
                # just set /etc/sysctl.conf, but not p
                if merge_dict[key] != live_dict[key]:
                    diff_list.append(key)
        else:
            # only sysctl -w OR live_value ( ex. fs.xfs.* )
            merge_dict[key] = ""
            org_dict[key] = ""
            live_load_list.append(key)
    return diff_list, live_load_list

if __name__ == "__main__":
    except_src = '/app/zabbix/etc/sysctl_except_list.txt'
    cmp_except_src = '/app/zabbix/etc/sysctl_compare_except_list.txt'
    live_except_src = '/app/zabbix/etc/sysctl_live_except_list.txt'
    org_src = '/etc/sysctl.conf.org'
    conf_src = '/etc/sysctl.conf'

    merge_dict = {}

    try:
    with open(except_src, 'r') as f:
            except_list = f.read().splitlines()
            except_list[:] = [s.split('#')[0].strip() for s in except_list if re.match(r'^\s*[^ #]+', s)]
    except:
    print except_src, 'file not found'
    sys.exit()

    try:
    with open(cmp_except_src, 'r') as f:
            cmp_except_list = f.read().splitlines()
            cmp_except_list[:] = [s.split('#')[0].strip() for s in cmp_except_list if re.match(r'^\s*[^ #]+', s)]
    except:
    print cmp_except_src, 'file not found'
    sys.exit()

    try:
    with open(live_except_src, 'r') as f:
        live_except_list = f.read().splitlines()
        live_except_list[:] = [s.split('#')[0].strip() for s in live_except_list if re.match(r'^\s*[^ #]+', s)]
    except:
    print live_except_src, 'file not found'
    sys.exit()

    try:
        with open(org_src, 'r') as f:
            org_lines = f.read().splitlines()
            org_dict = lines_to_dict(org_lines)
            merge_dict = org_dict.copy()
    except:
    print org_src, 'file not found'
    sys.exit()

    try:
        with open(conf_src, 'r') as f:
            conf_lines = f.read().splitlines()
            conf_dict = lines_to_dict(conf_lines)
    except:
    print conf_src, 'file not found'
    sys.exit()

    for key in conf_dict:
        merge_dict[key] = conf_dict[key]

    with open(os.devnull, 'w') as DEVNULL:
        try:
            live_list = subprocess.Popen(["sysctl", "-a"], stdout=subprocess.PIPE, stderr=DEVNULL).communicate()[0]
        except:
            print 'fail sysctl -a'

    live_dict = lines_to_dict(live_list.strip().split('\n'))

    n, key_len, value_len = calculate_line_length(except_list, live_dict)
    diff_list, live_load_list = verify_params(except_list, merge_dict, live_dict, key_len, value_len)

    # except that origin is null and live value exists
    org_dict_null_value = [ x for x in org_dict if org_dict[x] == "" ]
    combined = "|".join(live_except_list) or "No Live Exception List"
    for key in live_load_list[:]:
        if key in org_dict_null_value:
            if re.match(combined, key):
                live_load_list.remove(key)

    # except that live value is less than org+conf value
    combined = "|".join(cmp_except_list) or "No Compare Exception List"
    for key in diff_list[:]:
    if re.match(combined, key):
        if int(merge_dict[key]) < int(live_dict[key]):
            diff_list.remove(key)


    #### print part ####
    if len(diff_list) == 0:
    pass
    else:
        # print different parameters from live value
        print_horizontal_line(n)
        print_columns()
        print_horizontal_line(n)
        for key in diff_list:
        if key not in conf_dict.keys():
        conf_dict[key] = ""
            print '%*s %*s %*s %*s\n' % (-key_len, key, -value_len, org_dict[key], -value_len, conf_dict[key], -value_len, live_dict[key])
        print_horizontal_line(n)
        print 'total', len(diff_list)
    if len(live_load_list) == 0:
    pass
    else:
        #print live load parameters
        print_horizontal_line(n)
        print '%*s %*s' % (-key_len, 'Live Load Parameter', -value_len, 'LIVE VALUE')
        print_horizontal_line(n)
        for key in live_load_list:
            print '%*s %*s\n' % (-key_len, key, -value_len, live_dict[key])
        print_horizontal_line(n)
        print 'total', len(live_load_list)
