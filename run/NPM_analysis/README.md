
# Run the tool on the server at CNR

1. Enable the VPN connection to CNR.

2. Open a terminal and connect to the server using SSH:
```bash
ssh name@ip_address -p port_number
```

3. If not already in a tmux session, launch a new tmux session:
```bash
tmux new -s name_of_new_session
```

Using tmux allows you to keep the session running even if the connection is interrupted.
At this time, run the analysis with Docker.

-----------------------------------------------------------------------
### Run the analysis with Docker
-----------------------------------------------------------------------

4. If you want to stop the tmux session **without terminating the processes**, press `Ctrl + B`, then `D` to detach from the session.

5. To reattach to the tmux session later, use:
```bash
tmux ls                                 # to list existing sessions
tmux attach -t name_of_new_session      # to reattach to the desired session
```

