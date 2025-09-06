"""WebSocket event handlers for BertiBox."""

def register_handlers(socketio, get_berti_box):
    """Register all WebSocket event handlers.
    
    Args:
        socketio: The SocketIO instance
        get_berti_box: Function that returns the BertiBox instance
    """
    
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.emit_player_status)

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    @socketio.on('request_player_status')
    def handle_request_player_status():
        print('Received request for player status')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.emit_player_status)

    @socketio.on('play_pause')
    def handle_play_pause():
        print('Received play/pause command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(
                lambda: berti_box.pause_playback() if (berti_box.is_playing and not berti_box.is_paused) 
                else berti_box.resume_playback()
            )

    @socketio.on('play_track')
    def handle_play_track(data):
        index = data.get('index')
        print(f'Received play track command for index: {index}')
        berti_box = get_berti_box()
        if berti_box and index is not None:
            try:
                index_int = int(index)
                if berti_box.current_playlist and 0 <= index_int < len(berti_box.current_playlist_items):
                    socketio.start_background_task(
                        lambda idx=index_int: (
                            setattr(berti_box, 'current_playlist_index', idx),
                            berti_box.play_current_track()
                        )
                    )
                else:
                    print(f"Invalid index {index_int} for current playlist")
            except ValueError:
                print(f"Invalid index format: {index}")

    @socketio.on('pause')
    def handle_pause():
        print('Received pause command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.pause_playback)

    @socketio.on('resume')
    def handle_resume():
        print('Received resume command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.resume_playback)

    @socketio.on('next_track')
    def handle_next_track():
        print('Received next track command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.play_next)

    @socketio.on('previous_track')
    def handle_previous_track():
        print('Received previous track command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.play_previous)

    @socketio.on('set_volume')
    def handle_set_volume(data):
        volume = data.get('volume')
        print(f'Received set volume command: {volume}')
        berti_box = get_berti_box()
        if berti_box and volume is not None:
            try:
                vol_float = float(volume)
                if 0.0 <= vol_float <= 1.0:
                    socketio.start_background_task(
                        lambda v=vol_float: (
                            berti_box.set_volume_internal(v),
                            berti_box.emit_player_status()
                        )
                    )
                else:
                    print(f"Invalid volume value: {vol_float}")
            except ValueError:
                print(f"Invalid volume format: {volume}")

    @socketio.on('set_sleep_timer')
    def handle_set_sleep_timer(data):
        duration_minutes = data.get('duration')
        print(f'Received set sleep timer command: {duration_minutes} minutes')
        berti_box = get_berti_box()
        if berti_box and duration_minutes is not None:
            socketio.start_background_task(berti_box.set_sleep_timer, duration_minutes)

    @socketio.on('cancel_sleep_timer')
    def handle_cancel_sleep_timer():
        print('Received cancel sleep timer command')
        berti_box = get_berti_box()
        if berti_box:
            socketio.start_background_task(berti_box.cancel_sleep_timer)