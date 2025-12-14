import json
import os
from datetime import datetime
from flask import Flask
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from ytmusicapi import YTMusic

# Create Flask web app for Render
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🎵 YouTube Music Playlist Tracker Bot is running!"

@web_app.route('/health')
def health():
    return {
        "status": "healthy",
        "bot": "youtube-music-tracker",
        "timestamp": datetime.now().isoformat()
    }

def run_web():
    """Run Flask web server"""
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

# Configuration
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8243692539:AAEJA6TPk3abwyzfVPjrvUEnftQTH-qF9sg")
PLAYLIST_ID = os.environ.get("PLAYLIST_ID", "PLXd3ds-SIEMJfFfhlv2hpMwbzFwB3ambu")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "120"))
STORAGE_FILE = "playlist_state.json"

class PlaylistTracker:
    def __init__(self):
        # Use the browser.json file you just created
        self.ytmusic = YTMusic("browser.json")
        
    def get_playlist_tracks(self, playlist_id):
        """Fetch current playlist and return list of track info"""
        try:
            playlist = self.ytmusic.get_playlist(playlist_id, limit=None)
            tracks = []
            
            for track in playlist.get('tracks', []):
                track_info = {
                    'videoId': track.get('videoId'),
                    'title': track.get('title'),
                    'artists': ', '.join([a['name'] for a in track.get('artists', [])])
                }
                tracks.append(track_info)
            
            return tracks
        except Exception as e:
            print(f"Error fetching playlist: {e}")
            return None
    
    def compare_playlists(self, old_tracks, new_tracks):
        """Compare two playlist states and return added/removed songs"""
        old_ids = {t['videoId']: t for t in old_tracks}
        new_ids = {t['videoId']: t for t in new_tracks}
        
        added = [new_ids[vid] for vid in new_ids if vid not in old_ids]
        removed = [old_ids[vid] for vid in old_ids if vid not in new_ids]
        
        return added, removed
    
    def load_previous_state(self):
        """Load the last saved playlist state"""
        if os.path.exists(STORAGE_FILE):
            with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tracks', [])
        return []
    
    def save_current_state(self, tracks):
        """Save current playlist state to file"""
        with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'tracks': tracks,
                'last_updated': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)



# Initialize tracker
tracker = PlaylistTracker()
subscribed_chats = set()



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    # Get bot username
    bot = await context.bot.get_me()
    bot_username = bot.username
    
    # Create inline keyboard with "Add Bot to Group" button
    keyboard = [
        [InlineKeyboardButton("📖 Help", callback_data='help')],
        [InlineKeyboardButton("➕ Add Bot to Group", 
                            url=f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+delete_messages")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🎵 <b>Welcome to YouTube Music Playlist Tracker!</b>\n\n"
        "I track changes to your YouTube Music playlists and notify you when songs are "
        "added or removed!\n\n"
        "Use /help to see all available commands."
    )
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        help_text = (
    "🎵 <b>YouTube Music Playlist Tracker - Commands</b>\n\n"
    
    "<b>Setup Commands:</b>\n"
    "/setplaylist &lt;url&gt; - Change the playlist to track\n\n"
    
    "<b>Information Commands:</b>\n"
    "/status - Check current tracking status\n"
    "/help - Show this help message\n\n"
    
    "<b>Utility Commands:</b>\n"
    "/check - Manually check playlist now\n"
    "/subscribe - Get automatic notifications\n"
    "/unsubscribe - Stop notifications in this chat\n\n"
    
    "<b>Features:</b>\n"
    "✨ Automatic tracking every 2 minutes\n"
    "➕ Notifications when songs are added\n"
    "➖ Notifications when songs are removed\n"
    "💾 Remembers changes even when bot restarts\n"
    "🎨 Beautiful messages with album art\n\n"
    
    "<b>Quick Start:</b>\n"
    "1️⃣ Use /setplaylist with your playlist URL\n"
    "2️⃣ Use /subscribe to enable notifications\n"
    "3️⃣ That's it! Changes will be posted here automatically\n\n"
    
    "<i>Made with ❤️ for music lovers</i>"
        )
        await query.edit_message_text(text=help_text, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed help message"""
    help_text = (
        "🎵 <b>YouTube Music Playlist Tracker - Commands</b>\n\n"
        
        "<b>Setup Commands:</b>\n"
        "Already configured! The bot is tracking your playlist automatically.\n\n"
        
        "<b>Information Commands:</b>\n"
        "/status - Check current tracking status\n"
        "/help - Show this help message\n\n"
        
        "<b>Utility Commands:</b>\n"
        "/check - Manually check playlist now\n"
        "/subscribe - Get automatic notifications\n"
        "/unsubscribe - Stop notifications in this chat\n\n"
        
        "<b>Features:</b>\n"
        "✨ Automatic tracking every 2 minutes\n"
        "➕ Notifications when songs are added\n"
        "➖ Notifications when songs are removed\n"
        "💾 Remembers changes even when bot restarts\n"
        "🎨 Beautiful messages with album art\n\n"
        
        "<b>Quick Start:</b>\n"
        "1️⃣ Use /subscribe to enable notifications\n"
        "2️⃣ That's it! Changes will be posted here automatically\n\n"
        
        "<i>Made with ❤️ for music lovers</i>"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def send_track_card(update: Update, context: ContextTypes.DEFAULT_TYPE, track, change_type):
    """Send a formatted card for a track with album art"""
    try:
        # Get full track details
        video_info = tracker.ytmusic.get_song(track['videoId'])
        
        # Try multiple paths to get thumbnail
        thumbnail_url = None
        
        # Try videoDetails first
        if 'videoDetails' in video_info and 'thumbnail' in video_info['videoDetails']:
            thumbnails = video_info['videoDetails']['thumbnail'].get('thumbnails', [])
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Try top-level thumbnails
        if not thumbnail_url and 'thumbnails' in video_info:
            thumbnails = video_info['thumbnails']
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Get album name
        album = 'Unknown Album'
        if 'videoDetails' in video_info:
            album = video_info['videoDetails'].get('album', 'Unknown Album')
        elif 'album' in video_info:
            album = video_info['album'].get('name', 'Unknown Album')
        
        # Get duration
        duration_seconds = 0
        if 'videoDetails' in video_info:
            duration_seconds = int(video_info['videoDetails'].get('lengthSeconds', 0))
        elif 'duration_seconds' in video_info:
            duration_seconds = int(video_info.get('duration_seconds', 0))
        
        duration = f"{duration_seconds // 60}:{duration_seconds % 60:02d}" if duration_seconds else "Unknown"
        
        # Format message
        if change_type == "added":
            emoji = "➕"
            header = "Song Added!"
        else:
            emoji = "➖"
            header = "Song Removed!"
        
        caption = (
            f"{emoji} <b>{header}</b>\n\n"
            f"🎵 <b>{track['title']}</b>\n"
            f"👤 Artist: {track['artists']}\n"
            f"💿 Album: {album}\n"
            f"⏱ Duration: {duration}"
        )
        
        # Send photo with caption
        if thumbnail_url:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=thumbnail_url,
                caption=caption,
                parse_mode='HTML'
            )
        else:
            # Fallback if no thumbnail
            await update.message.reply_text(caption, parse_mode='HTML')
            
    except Exception as e:
        print(f"Error in send_track_card: {e}")
        # Fallback to simple message if detailed fetch fails
        emoji = "➕" if change_type == "added" else "➖"
        simple_msg = f"{emoji} {track['title']} - {track['artists']}"
        await update.message.reply_text(simple_msg)


async def check_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually check playlist for changes"""
    await update.message.reply_text("🔍 Checking playlist...")
    
    current_tracks = tracker.get_playlist_tracks(PLAYLIST_ID)
    
    if current_tracks is None:
        await update.message.reply_text("❌ Error fetching playlist. Check your configuration.")
        return
    
    previous_tracks = tracker.load_previous_state()
    
    if not previous_tracks:
        tracker.save_current_state(current_tracks)
        await update.message.reply_text(
            f"✅ Initialized! Tracking {len(current_tracks)} songs.\n"
            "Use /check again to see changes."
        )
        return
    
    added, removed = tracker.compare_playlists(previous_tracks, current_tracks)
    
    # Send summary first
    summary = f"📊 Playlist Update ({datetime.now().strftime('%I:%M %p')})\n\n"
    if added:
        summary += f"➕ Added: {len(added)}\n"
    if removed:
        summary += f"➖ Removed: {len(removed)}\n"
    if not added and not removed:
        summary += "✨ No changes detected"
    
    await update.message.reply_text(summary)
    
    # Send detailed cards for removed songs
    if removed:
        for track in removed:
            await send_track_card(update, context, track, "removed")
    
    # Send detailed cards for added songs
    if added:
        for track in added:
            await send_track_card(update, context, track, "added")
    
    tracker.save_current_state(current_tracks)



async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Subscribe to automatic updates"""
    chat_id = update.effective_chat.id
    subscribed_chats.add(chat_id)
    await update.message.reply_text("✅ Subscribed! You'll receive automatic updates.")



async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unsubscribe from updates"""
    chat_id = update.effective_chat.id
    subscribed_chats.discard(chat_id)
    await update.message.reply_text("❌ Unsubscribed from automatic updates.")



async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check subscription status and show playlist details"""
    chat_id = update.effective_chat.id
    is_subscribed = chat_id in subscribed_chats
    
    try:
        # Get playlist details
        playlist_data = tracker.ytmusic.get_playlist(PLAYLIST_ID, limit=None)
        
        # Extract playlist info
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        playlist_author = playlist_data.get('author', {}).get('name', 'Unknown')
        total_songs = len(playlist_data.get('tracks', []))
        
        # Get playlist thumbnail
        thumbnail_url = None
        if 'thumbnails' in playlist_data:
            thumbnails = playlist_data['thumbnails']
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Format check interval
        interval_minutes = CHECK_INTERVAL // 60
        interval_text = f"Every {interval_minutes} minute{'s' if interval_minutes != 1 else ''}"
        
        # Build status message
        status_emoji = "✅" if is_subscribed else "❌"
        status_text = "Active" if is_subscribed else "Inactive"
        
        caption = (
            f"🎵 <b>Playlist Tracker Status</b>\n\n"
            f"<b>Current Playlist:</b>\n"
            f"<a href='https://music.youtube.com/playlist?list={PLAYLIST_ID}'>{playlist_title}</a>\n\n"
            f"📊 <b>Total Songs:</b> {total_songs}\n"
            f"⏱ <b>Check Interval:</b> {interval_text}\n"
            f"{status_emoji} <b>Status:</b> {status_text}\n\n"
            f"<b>YouTube Music</b>\n"
            f"{playlist_title}\n"
            f"Playlist · {playlist_author} · {total_songs} items"
        )
        
        # Send with thumbnail if available
        if thumbnail_url:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=thumbnail_url,
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(caption, parse_mode='HTML')
            
    except Exception as e:
        print(f"Error in status command: {e}")
        # Fallback to simple status
        status_text = "✅ Subscribed" if is_subscribed else "❌ Not subscribed"
        await update.message.reply_text(f"Status: {status_text}")

async def setplaylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or change the playlist to track"""
    global PLAYLIST_ID
    
    # Check if playlist ID/URL is provided
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Usage:</b> /setplaylist &lt;playlist_id_or_url&gt;\n\n"
            "<b>Examples:</b>\n"
            "• /setplaylist PLXd3ds-SIEMJfFfhlv2hpMwbzFwB3ambu\n"
            "• /setplaylist https://music.youtube.com/playlist?list=PLXd3ds-SIEMJfFfhlv2hpMwbzFwB3ambu\n\n"
            "<i>You can copy the URL from YouTube Music app or browser</i>",
            parse_mode='HTML'
        )
        return
    
    # Get the argument (playlist ID or URL)
    input_text = context.args[0]
    
    # Extract playlist ID from URL if URL is provided
    if 'list=' in input_text:
        try:
            playlist_id = input_text.split('list=')[1].split('&')[0]
        except:
            await update.message.reply_text("❌ Invalid playlist URL format")
            return
    else:
        playlist_id = input_text
    
    # Validate playlist ID format (YouTube playlist IDs start with PL and are ~34 chars)
    if not playlist_id.startswith('PL') or len(playlist_id) < 20:
        await update.message.reply_text(
            "❌ Invalid playlist ID format.\n\n"
            "Playlist IDs should start with 'PL' and be around 34 characters long."
        )
        return
    
    # Try to fetch the playlist to validate it exists
    await update.message.reply_text("🔍 Checking playlist...")
    
    try:
        playlist_data = tracker.ytmusic.get_playlist(playlist_id, limit=5)
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        playlist_author = playlist_data.get('author', {}).get('name', 'Unknown')
        total_songs = playlist_data.get('trackCount', len(playlist_data.get('tracks', [])))
        
        # Get playlist thumbnail
        thumbnail_url = None
        if 'thumbnails' in playlist_data:
            thumbnails = playlist_data['thumbnails']
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Update the global playlist ID
        old_playlist_id = PLAYLIST_ID
        PLAYLIST_ID = playlist_id
        
        # Clear the old state file to start fresh
        if os.path.exists(STORAGE_FILE):
            os.remove(STORAGE_FILE)
        
        # Success message
        caption = (
            f"✅ <b>Playlist Updated Successfully!</b>\n\n"
            f"<b>Now Tracking:</b>\n"
            f"<a href='https://music.youtube.com/playlist?list={playlist_id}'>{playlist_title}</a>\n\n"
            f"📊 <b>Total Songs:</b> {total_songs}\n"
            f"👤 <b>Author:</b> {playlist_author}\n\n"
            f"<i>Use /check to initialize tracking</i>"
        )
        
        if thumbnail_url:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=thumbnail_url,
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(caption, parse_mode='HTML')
        
        print(f"Playlist changed from {old_playlist_id} to {PLAYLIST_ID}")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Error accessing playlist</b>\n\n"
            f"Please check:\n"
            f"• The playlist ID is correct\n"
            f"• The playlist is public or unlisted\n"
            f"• You have access to this playlist\n\n"
            f"Error: {str(e)}",
            parse_mode='HTML'
        )
        print(f"Error setting playlist: {e}")

async def send_track_card_direct(context: ContextTypes.DEFAULT_TYPE, chat_id, track, change_type):
    """Send track card directly to a chat_id (for periodic checks)"""
    try:
        video_info = tracker.ytmusic.get_song(track['videoId'])
        
        # Try multiple paths to get thumbnail
        thumbnail_url = None
        
        # Try videoDetails first
        if 'videoDetails' in video_info and 'thumbnail' in video_info['videoDetails']:
            thumbnails = video_info['videoDetails']['thumbnail'].get('thumbnails', [])
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Try top-level thumbnails
        if not thumbnail_url and 'thumbnails' in video_info:
            thumbnails = video_info['thumbnails']
            if thumbnails:
                thumbnail_url = thumbnails[-1]['url']
        
        # Get album name
        album = 'Unknown Album'
        if 'videoDetails' in video_info:
            album = video_info['videoDetails'].get('album', 'Unknown Album')
        elif 'album' in video_info:
            album = video_info['album'].get('name', 'Unknown Album')
        
        # Get duration
        duration_seconds = 0
        if 'videoDetails' in video_info:
            duration_seconds = int(video_info['videoDetails'].get('lengthSeconds', 0))
        elif 'duration_seconds' in video_info:
            duration_seconds = int(video_info.get('duration_seconds', 0))
        
        duration = f"{duration_seconds // 60}:{duration_seconds % 60:02d}" if duration_seconds else "Unknown"
        
        if change_type == "added":
            emoji = "➕"
            header = "Song Added!"
        else:
            emoji = "➖"
            header = "Song Removed!"
        
        caption = (
            f"{emoji} <b>{header}</b>\n\n"
            f"🎵 <b>{track['title']}</b>\n"
            f"👤 Artist: {track['artists']}\n"
            f"💿 Album: {album}\n"
            f"⏱ Duration: {duration}"
        )
        
        if thumbnail_url:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=thumbnail_url,
                caption=caption,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=caption, parse_mode='HTML')
            
    except Exception as e:
        print(f"Error in send_track_card_direct: {e}")
        simple_msg = f"{'➕' if change_type == 'added' else '➖'} {track['title']} - {track['artists']}"
        await context.bot.send_message(chat_id=chat_id, text=simple_msg)


async def periodic_check(context: ContextTypes.DEFAULT_TYPE):
    """Periodically check playlist and notify subscribers"""
    current_tracks = tracker.get_playlist_tracks(PLAYLIST_ID)
    
    if current_tracks is None:
        return
    
    previous_tracks = tracker.load_previous_state()
    
    if not previous_tracks:
        tracker.save_current_state(current_tracks)
        return
    
    added, removed = tracker.compare_playlists(previous_tracks, current_tracks)
    
    if added or removed:
        # Send to all subscribed chats
        for chat_id in subscribed_chats:
            try:
                # Send summary
                summary = f"🔔 Playlist Changed! ({datetime.now().strftime('%I:%M %p')})\n\n"
                if added:
                    summary += f"➕ Added: {len(added)}\n"
                if removed:
                    summary += f"➖ Removed: {len(removed)}"
                
                await context.bot.send_message(chat_id=chat_id, text=summary)
                
                # Send cards for removed songs
                for track in removed:
                    await send_track_card_direct(context, chat_id, track, "removed")
                
                # Send cards for added songs
                for track in added:
                    await send_track_card_direct(context, chat_id, track, "added")
                    
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}")
        
        tracker.save_current_state(current_tracks)


def main():
    """Start the bot"""
    try:
        # Start Flask web server in background thread
        print("Starting web server...")
        threading.Thread(target=run_web, daemon=True).start()
        
        print("Initializing bot application...")
        app = Application.builder().token(BOT_TOKEN).build()
        
        print("Adding command handlers...")
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("setplaylist", setplaylist))
        app.add_handler(CommandHandler("check", check_playlist))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe))
        app.add_handler(CommandHandler("status", status))
        
        # Add callback query handler for buttons
        app.add_handler(CallbackQueryHandler(button_callback))
        
        # Schedule periodic checks
        if app.job_queue:
            print("Setting up job queue...")
            app.job_queue.run_repeating(periodic_check, interval=CHECK_INTERVAL, first=10)
            print(f"✅ Bot started! Checking playlist every {CHECK_INTERVAL} seconds")
        else:
            print("⚠️ Job queue not available. Install python-telegram-bot[job-queue]")
        
        print("Starting polling...")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        import traceback
        traceback.print_exc()