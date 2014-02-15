"""
Copyright (c) 2013-2014, Sam Dodrill & AppleDash
All rights reserved.

This software is provided 'as-is', without any express or implied
warranty. In no event will the authors be held liable for any damages
arising from the use of this software.

Permission is granted to anyone to use this software for any purpose,
including commercial applications, and to alter it and redistribute it
freely, subject to the following restrictions:

    1. The origin of this software must not be misrepresented; you must not
    claim that you wrote the original software. If you use this software
    in a product, an acknowledgment in the product documentation would be
    appreciated but is not required.

    2. Altered source versions must be plainly marked as such, and must not be
    misrepresented as being the original software.

    3. This notice may not be removed or altered from any source
    distribution.
"""

import sys

from structures import *
from utils import *
from protocol import UnrealServerConn

NAME="UnrealIRCd protocol module"
DESC="Handles login and protocol commands for UnrealIRCd"

def initModule(cod):
    cod.loginFunc = login
    cod.burstClient = burstClient
    cod.tsSecond = False
    cod.protocol = UnrealServerConn(cod)

    cod.s2scommands["NICK"] = [handleNICK]
    cod.s2scommands["PING"] = [handlePING]

    cod.s2scommands["PRIVMSG"].append(handlePRIVMSG)

def destroyModule(cod):
    del cod.loginFunc
    cod.loginFunc = None
    del cod.burstClient
    cod.burstClient = None

    del cod.s2scommands["NICK"]
    del cod.s2scommands["PING"]

    cod.s2scommands["PRIVMSG"].remove(handlePRIVMSG)

def rehash():
    pass

def login(cod):
    """
    Sends the commands needed to authenticate to the remote IRC server.
    """
    cod.sendLine("PASS %s" % (cod.config["uplink"]["pass"],))
    cod.sendLine("PROTOCTL NICKv2 VHP NICKIP UMODE2 SJOIN SJOIN2 SJ3 NOQUIT TKLEXT ESVID")
    cod.sendLine("PROTOCTL SID=%s" % (cod.sid,))
    cod.sendLine("SERVER %s 1 :%s" % (cod.config["me"]["name"], cod.config["me"]["desc"]))
    cod.sendLine(":%s EOS" % (cod.config["me"]["name"],))

def burstClient(cod, client):
    client.uid = client.nick
    cod.sendLine("NICK %s 1 %s %s %s %s * %s * :%s" % (client.nick, client.ts, client.user, client.host, cod.config["me"]["name"], client.modes, client.gecos))

def nullCommand(cod, line):
    """
    Useful for ignoring commands that should be implemented later
    """
    pass

def handleNICK(cod, line):
    """
        Listens for NICK commands and adds information about remote clients.
    """
    # <<< NICK Xe 2 1391891416 sid16693 charlton.irccloud.com cox.split.net 1 +iwx split-A0A2E838.irccloud.com wLgJcA== :Xe
    # NICK <nick> <hops> <ts> <ident> <realhost> <homeserver> <wtflol> <modes> <cloakedhost> <wtflol> <realname>
    #        0       1     2     3         4          5           6       7          8          9         10

    #    def __init__(self, nick, uid, ts, modes, user, host, ip, login, gecos):
    if len(line.args) <= 2:
        cod.clients[line.sender].nick = line.args[0]
        cod.clients[line.sender].uid = cod.clients[line.sender].nick
    client = Client(line.args[0], line.args[0], line.args[2], line.args[7], line.args[3], line.args[8], line.args[4], "", line.args[-1])
    client.uid = client.nick
    if "o" in client.modes:
        client.isOper = True
    cod.clients[client.uid] = client
    cod.runHooks("newclient", [client])

def handlePRIVMSG(cod, line):
    """
    Handle PRIVMSG
    """
    print "HANDLING THAT JUNK"
    line.source = cod.clients[line.source]

    destination = line.args[0]

    if destination[0] == "#":
        cod.runHooks("chanmsg", [cod.channels[line.args[0]], line])
    else:
        cod.runHooks("privmsg", [cod.clients[line.args[0]], line])

    source = line.source
    line = line.args[-1]
    splitline = line.split()

    command = ""
    pm = True
    print "PARSED"

    if destination[0] == "#":
        if destination not in cod.client.channels:
            return
        try:
            if line[0] == cod.config["me"]["prefix"]:
                command = splitline[0].upper()
                command = command[1:]
                pm = False
        except IndexError as e:
            #print str(e)
            return

    elif destination != cod.client.uid and pm:
        return

    else:
        destination = cod.clients[destination]
        command = splitline[0].upper()
    print "ENTIERING TRY LOOP"
    #Guido, I am sorry.
    try:
        print "FUCK"
        if source.isOper:
            print "OPER"
            for impl in cod.opercommands[command]:
                print "ITS AN IMPL"
                try:
                    if pm:
                        impl(cod, line, splitline, source, source)
                    else:
                        impl(cod, line, splitline, source, destination)
                except Exception as e:
                    cod.servicesLog("%s: %s" % (type(e), e.message))
                    continue
        else:
            print "RAISING"
            raise KeyError

    except KeyError as e:
        for impl in cod.botcommands[command]:

            try:
                if pm:
                    impl(cod, line, splitline, source, source)
                else:
                    impl(cod, line, splitline, source, destination)
            except Exception as e:
                cod.servicesLog("%s: %s" % (type(e), e.message))
    except KeyError as e:
        return
    except Exception as e:
        cod.servicesLog("%s: %s" % (type(e), e.message))

def handlePING(cod, line):
    """
    Pongs remote servers to end bursting
    """

    if not cod.bursted:
        #Join staff and snoop channels
        cod.join(cod.config["etc"]["staffchan"])
        cod.join(cod.config["etc"]["snoopchan"])
        cod.privmsg("NickServ", "IDENTIFY %s" % cod.config["me"]["servicespass"])

        #Load admin module
        cod.loadmod("admin") #Required to be hard-coded
        cod.loadmod("help")

        cod.bursted = True

    cod.sendLine(":%s PONG %s :%s" %
            (cod.sid, cod.config["me"]["name"],
                line.source))

