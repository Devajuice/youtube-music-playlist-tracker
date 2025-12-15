import os
import time
import asyncio
from dotenv import load_dotenv
from ytmusicapi import YTMusic
from telegram import Update, Bot, InputMediaPhoto
from telegram.ext import Application, CommandHandler, ContextTypes
from keep_alive import keep_alive
import json
import requests
from io import BytesIO






# Load environment variables
load_dotenv()






TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
YOUTUBE_PLAYLIST_ID = os.getenv('YOUTUBE_PLAYLIST_ID')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 300))  # Default: 5 minutes






# Initialize APIs
ytmusic = YTMusic()






# Store files
PLAYLIST_FILE = 'playlist_state.json'
SUBSCRIBERS_FILE = 'subscribers.json'






def load_subscribers():
    """Load list of subscribed chat IDs"""
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading subscribers: {e}")
        return []






def save_subscribers(subscribers):
    """Save list of subscribed chat IDs"""
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump(subscribers, f, indent=2)
    except Exception as e:
        print(f"Error saving subscribers: {e}")






async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - Subscribe user to notifications"""
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    
    if chat_id not in subscribers:
        subscribers.append(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text(
            "✅ <b>Welcome to YouTube Music Playlist Monitor!</b>\n\n"
            "You are now subscribed to playlist updates.\n"
            "You'll receive notifications when songs are added or removed.\n\n"
            "<b>Commands:</b>\n"
            "/start - Subscribe to notifications\n"
            "/stop - Unsubscribe from notifications\n"
            "/status - Check current status\n"
            "/check - Force check playlist now\n"
            "/help - Show detailed help\n\n"
            "Use /help for more information! 📚",
            parse_mode='HTML'
        )
        print(f"New subscriber: {chat_id}")
    else:
        await update.message.reply_text(
            "ℹ️ You're already subscribed to playlist updates!",
            parse_mode='HTML'
        )






async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stop command - Unsubscribe user from notifications"""
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    
    if chat_id in subscribers:
        subscribers.remove(chat_id)
        save_subscribers(subscribers)
        await update.message.reply_text(
            "👋 You have been unsubscribed from playlist updates.\n"
            "Send /start anytime to subscribe again!",
            parse_mode='HTML'
        )
        print(f"Unsubscribed: {chat_id}")
    else:
        await update.message.reply_text(
            "ℹ️ You're not currently subscribed.",
            parse_mode='HTML'
        )






async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - Show current status"""
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    
    is_subscribed = chat_id in subscribers
    total_subscribers = len(subscribers)
    
    playlist_tracks = get_playlist_tracks()
    track_count = len(playlist_tracks) if playlist_tracks else "Unknown"
    
    status_message = (
        f"📊 <b>Bot Status</b>\n\n"
        f"Your Status: {'✅ Subscribed' if is_subscribed else '❌ Not Subscribed'}\n"
        f"Total Subscribers: {total_subscribers}\n"
        f"Playlist Songs: {track_count}\n"
        f"Check Interval: {CHECK_INTERVAL // 60} minutes\n\n"
        f"Send /start to subscribe!"
    )
    
    await update.message.reply_text(status_message, parse_mode='HTML')






async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /check command - Manually trigger playlist check"""
    chat_id = update.effective_chat.id
    subscribers = load_subscribers()
    
    if chat_id not in subscribers:
        await update.message.reply_text(
            "⚠️ Please subscribe first using /start",
            parse_mode='HTML'
        )
        return
    
    await update.message.reply_text("🔄 Checking playlist for updates...", parse_mode='HTML')
    
    # Perform check for this user only
    await check_playlist_for_user(chat_id, context.bot)






async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - Show help information"""
    help_text = (
        "🎵 <b>YouTube Music Playlist Monitor Bot</b>\n\n"
        "This bot monitors your YouTube Music playlist and sends you notifications "
        "whenever songs are added or removed.\n\n"
        "<b>📋 Available Commands:</b>\n\n"
        "/start - Subscribe to playlist notifications\n"
        "/stop - Unsubscribe from notifications\n"
        "/status - View bot status and your subscription info\n"
        "/check - Manually check for playlist updates now\n"
        "/help - Show this help message\n\n"
        "<b>⚙️ How It Works:</b>\n\n"
        "• The bot checks your playlist every 5 minutes\n"
        "• You'll get a notification with album art when songs are added ➕\n"
        "• You'll get a notification when songs are removed ➖\n"
        "• Each notification includes song title, artist, and a direct link\n\n"
        "<b>💡 Tips:</b>\n\n"
        "• Use /check to test the bot immediately\n"
        "• Use /status to see how many songs are being tracked\n"
        "• The bot runs 24/7 so you never miss updates!\n\n"
        "Enjoy your music tracking! 🎶"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')






def get_playlist_tracks():
    """Fetch current tracks from YouTube Music playlist"""
    try:
        playlist = ytmusic.get_playlist(YOUTUBE_PLAYLIST_ID, limit=None)
        tracks = []
        for track in playlist['tracks']:
            # Get the best quality SQUARE thumbnail (not wide)
            thumbnail = None
            if track.get('thumbnails'):
                # YouTube Music thumbnails - get the largest square one
                for thumb in reversed(track['thumbnails']):
                    if thumb.get('width') == thumb.get('height'):  # Square thumbnail
                        thumbnail = thumb['url']
                        break
                # Fallback to any thumbnail if no square found
                if not thumbnail and track['thumbnails']:
                    thumbnail = track['thumbnails'][-1]['url']
            
            tracks.append({
                'videoId': track.get('videoId'),
                'title': track.get('title'),
                'artists': ', '.join([artist['name'] for artist in track.get('artists', [])]),
                'thumbnail': thumbnail
            })
        return tracks
    except Exception as e:
        print(f"Error fetching playlist: {e}")
        return None






def load_previous_state():
    """Load previous playlist state from file"""
    try:
        if os.path.exists(PLAYLIST_FILE):
            with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data
        return []
    except Exception as e:
        print(f"Error loading previous state: {e}")
        return []






def save_current_state(tracks):
    """Save current playlist state to file"""
    try:
        # Save full track data so we have it when songs are removed
        with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(tracks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state: {e}")






def compare_playlists(old_tracks, new_tracks):
    """Compare two playlist states and return added/removed songs"""
    # Create sets of video IDs only
    old_ids = {track['videoId'] for track in old_tracks if track.get('videoId')}
    new_ids = {track['videoId'] for track in new_tracks if track.get('videoId')}
    
    added_ids = new_ids - old_ids
    removed_ids = old_ids - new_ids
    
    # Get full track info for added songs (from new_tracks which has all data)
    added_songs = [track for track in new_tracks if track['videoId'] in added_ids]
    
    # For removed songs, get data from old_tracks, but add placeholders if missing
    removed_songs = []
    for track in old_tracks:
        if track['videoId'] in removed_ids:
            # Ensure all required fields exist
            removed_song = {
                'videoId': track.get('videoId'),
                'title': track.get('title', 'Unknown Title'),
                'artists': track.get('artists', 'Unknown Artist'),
                'thumbnail': track.get('thumbnail', None)
            }
            removed_songs.append(removed_song)
    
    print(f"Comparison: {len(old_ids)} old tracks, {len(new_ids)} new tracks")
    print(f"Found: {len(added_songs)} added, {len(removed_songs)} removed")
    
    return added_songs, removed_songs






def format_song_caption(song, action):
    """Format song caption for photo message"""
    if action == "added":
        emoji = "➕"
        title = "Song Added!"
    else:
        emoji = "➖"
        title = "Song Removed!"
    
    # Safely get song data with defaults
    song_title = song.get('title', 'Unknown Title')
    song_artists = song.get('artists', 'Unknown Artist')
    song_video_id = song.get('videoId', '')
    
    caption = (
        f"<b>{emoji} {title}</b>\n\n"
        f"🎵 <b>{song_title}</b>\n"
        f"👤 Artist: {song_artists}\n"
        f"💿 Album: YouTube Music\n\n"
        f"🔗 <a href='https://music.youtube.com/watch?v={song_video_id}'>Listen on YouTube Music</a>"
    )
    
    return caption






def download_image(url):
    """Download image from URL and return as BytesIO"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return BytesIO(response.content)
        return None
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None






async def send_song_card_to_subscribers(bot, song, action):
    """Send song card with thumbnail to all subscribers"""
    subscribers = load_subscribers()
    caption = format_song_caption(song, action)
    
    # Download image once if thumbnail exists
    image_data = None
    if song.get('thumbnail'):
        image_data = download_image(song['thumbnail'])
    
    for chat_id in subscribers:
        try:
            if image_data:
                # Reset buffer position for each send
                image_data.seek(0)
                # Send photo (not document) - Telegram will display it inline
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image_data,
                    caption=caption,
                    parse_mode='HTML'
                )
            else:
                # Fallback to text message if no thumbnail
                await bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"Failed to send to {chat_id}: {e}")






async def check_playlist_for_user(chat_id, bot):
    """Check playlist and send update to specific user"""
    current_tracks = get_playlist_tracks()
    previous_tracks = load_previous_state()
    
    if not current_tracks:
        await bot.send_message(chat_id=chat_id, text="❌ Failed to fetch playlist", parse_mode='HTML')
        return
    
    if not previous_tracks:
        save_current_state(current_tracks)
        await bot.send_message(
            chat_id=chat_id,
            text=f"✅ Playlist loaded! Currently tracking {len(current_tracks)} songs.",
            parse_mode='HTML'
        )
        return
    
    added_songs, removed_songs = compare_playlists(previous_tracks, current_tracks)
    
    if added_songs or removed_songs:
        # Send individual card for each added song
        if added_songs:
            for song in added_songs:
                caption = format_song_caption(song, "added")
                if song.get('thumbnail'):
                    image_data = download_image(song['thumbnail'])
                    if image_data:
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=image_data,
                            caption=caption,
                            parse_mode='HTML'
                        )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=caption,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                await asyncio.sleep(0.5)
        
        # Send individual card for each removed song
        if removed_songs:
            for song in removed_songs:
                caption = format_song_caption(song, "removed")
                if song.get('thumbnail'):
                    image_data = download_image(song['thumbnail'])
                    if image_data:
                        await bot.send_photo(
                            chat_id=chat_id,
                            photo=image_data,
                            caption=caption,
                            parse_mode='HTML'
                        )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=caption,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                await asyncio.sleep(0.5)
        
        # Update state after sending notifications
        save_current_state(current_tracks)
    else:
        await bot.send_message(
            chat_id=chat_id,
            text="ℹ️ No changes detected in the playlist.",
            parse_mode='HTML'
        )






async def check_playlist(bot):
    """Main function to check playlist and send notifications to all subscribers"""
    print("Checking playlist for changes...")
    
    current_tracks = get_playlist_tracks()
    if current_tracks is None:
        print("Failed to fetch playlist")
        return
    
    previous_tracks = load_previous_state()
    
    if not previous_tracks:
        # First run - just save the state
        save_current_state(current_tracks)
        print(f"Initial state saved: {len(current_tracks)} songs")
        return
    
    added_songs, removed_songs = compare_playlists(previous_tracks, current_tracks)
    
    # Send individual card for each added song
    if added_songs:
        for song in added_songs:
            await send_song_card_to_subscribers(bot, song, "added")
            await asyncio.sleep(0.5)
        print(f"{len(added_songs)} songs added")
    
    # Send individual card for each removed song
    if removed_songs:
        for song in removed_songs:
            await send_song_card_to_subscribers(bot, song, "removed")
            await asyncio.sleep(0.5)
        print(f"{len(removed_songs)} songs removed")
    
    if added_songs or removed_songs:
        save_current_state(current_tracks)
    else:
        print("No changes detected")






async def periodic_check(application: Application):
    """Periodic task to check playlist"""
    while True:
        try:
            await check_playlist(application.bot)
        except Exception as e:
            print(f"Error in periodic check: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL)






def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start Flask server for UptimeRobot
    keep_alive()
    
    print("🤖 Bot started successfully!")
    
    # Start periodic checking in background
    application.job_queue.run_once(
        lambda context: asyncio.create_task(periodic_check(application)),
        when=1
    )
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)






if __name__ == '__main__':
    main()
