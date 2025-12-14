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


# Configuration - Use environment variables for deployment
BOT_TOKEN = os.environ.get("BOT_TOKEN")
PLAYLIST_ID = os.environ.get("PLAYLIST_ID")
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "120"))
STORAGE_FILE = "playlist_state.json"


class PlaylistTracker:
    def __init__(self):
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
    bot = await context.bot.get_me()
    bot_username = bot.username
    
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
            "/setplaylist &lt;url&gt; - Change the playlist to track\n"
            "/reset - Reset playlist state\n\n"
            
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
        "/setplaylist &lt;url&gt; - Change the playlist to track\n"
        "/reset - Reset playlist state\n\n"
        
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
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def check_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually check playlist for changes"""
    await update.message.reply_text("🔍 Checking playlist...")
    
    # Force fresh fetch from YouTube Music
    current_tracks = tracker.get_playlist_tracks(PLAYLIST_ID)
    
    if current_tracks is None:
        await update.message.reply_text("❌ Error fetching playlist. Check your configuration.")
        return
    
    # Load previous state
    previous_tracks = tracker.load_previous_state()
    
    if not previous_tracks:
        # First time - initialize
        tracker.save_current_state(current_tracks)
        await update.message.reply_text(
            f"✅ Initialized! Tracking {len(current_tracks)} songs.\n"
            "Use /check again to see changes."
        )
        return
    
    # Compare tracks
    added, removed = tracker.compare_playlists(previous_tracks, current_tracks)
    
    # Build response message with counts
    summary = (
        f"📊 <b>Playlist Update</b> ({datetime.now().strftime('%I:%M %p')})\n\n"
        f"Previous: {len(previous_tracks)} songs\n"
        f"Current: {len(current_tracks)} songs\n\n"
    )
    
    if added:
        summary += f"➕ <b>Added ({len(added)}):</b>\n"
        for track in added[:10]:  # Show max 10
            summary += f"  • {track['title']} - {track['artists']}\n"
        if len(added) > 10:
            summary += f"  ... and {len(added) - 10} more\n"
        summary += "\n"
    
    if removed:
        summary += f"➖ <b>Removed ({len(removed)}):</b>\n"
        for track in removed[:10]:  # Show max 10
            summary += f"  • {track['title']} - {track['artists']}\n"
        if len(removed) > 10:
            summary += f"  ... and {len(removed) - 10} more\n"
        summary += "\n"
    
    if not added and not removed:
        summary += "✨ <b>No changes detected</b>"
    
    await update.message.reply_text(summary, parse_mode='HTML')
    
    # Save current state for next comparison
    tracker.save_current_state(current_tracks)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset playlist state and reinitialize"""
    try:
        if os.path.exists(STORAGE_FILE):
            os.remove(STORAGE_FILE)
            await update.message.reply_text("✅ Playlist state reset! Use /check to reinitialize.")
        else:
            await update.message.reply_text("ℹ️ No saved state found. Use /check to initialize.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


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
        # Fetch fresh playlist data
        playlist_data = tracker.ytmusic.get_playlist(PLAYLIST_ID, limit=None)
        
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        playlist_author = 'Unknown'
        
        if 'author' in playlist_data:
            if isinstance(playlist_data['author'], dict):
                playlist_author = playlist_data['author'].get('name', 'Unknown')
            elif isinstance(playlist_data['author'], str):
                playlist_author = playlist_data['author']
        
        # Get REAL-TIME track count from actual playlist
        tracks = playlist_data.get('tracks', [])
        total_songs = len(tracks)
        
        # If tracks is empty but trackCount exists, use that
        if total_songs == 0 and 'trackCount' in playlist_data:
            total_songs = playlist_data['trackCount']
        
        thumbnail_url = None
        if 'thumbnails' in playlist_data and playlist_data['thumbnails']:
            thumbnail_url = playlist_data['thumbnails'][-1]['url']
        
        interval_minutes = CHECK_INTERVAL // 60
        interval_text = f"Every {interval_minutes} minute{'s' if interval_minutes != 1 else ''}"
        
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
        import traceback
        traceback.print_exc()
        status_text = "✅ Subscribed" if is_subscribed else "❌ Not subscribed"
        await update.message.reply_text(f"Status: {status_text}")


async def setplaylist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set or change the playlist to track"""
    global PLAYLIST_ID
    
    if not context.args:
        await update.message.reply_text(
            "❌ <b>Usage:</b> /setplaylist &lt;playlist_id_or_url&gt;\n\n"
            "<b>Examples:</b>\n"
            "• /setplaylist PLXd3ds-SIEMJfFfhlv2hpMwbzFwB3ambu\n"
            "• /setplaylist https://music.youtube.com/playlist?list=PLXd3ds-SIEMJfFfhlv2hpMwbzFwB3ambu",
            parse_mode='HTML'
        )
        return
    
    input_text = context.args[0]
    
    if 'list=' in input_text:
        try:
            playlist_id = input_text.split('list=')[1].split('&')[0]
        except:
            await update.message.reply_text("❌ Invalid playlist URL format")
            return
    else:
        playlist_id = input_text
    
    if not playlist_id.startswith('PL') or len(playlist_id) < 20:
        await update.message.reply_text("❌ Invalid playlist ID format.")
        return
    
    await update.message.reply_text("🔍 Checking playlist...")
    
    try:
        playlist_data = tracker.ytmusic.get_playlist(playlist_id, limit=5)
        playlist_title = playlist_data.get('title', 'Unknown Playlist')
        
        PLAYLIST_ID = playlist_id
        
        if os.path.exists(STORAGE_FILE):
            os.remove(STORAGE_FILE)
        
        await update.message.reply_text(
            f"✅ <b>Playlist Updated!</b>\n\n"
            f"Now tracking: {playlist_title}\n\n"
            f"Use /check to initialize tracking",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")


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
        for chat_id in subscribed_chats:
            try:
                summary = f"🔔 Playlist Changed! ({datetime.now().strftime('%I:%M %p')})\n\n"
                if added:
                    summary += f"➕ Added: {len(added)}\n"
                if removed:
                    summary += f"➖ Removed: {len(removed)}"
                
                await context.bot.send_message(chat_id=chat_id, text=summary)
                    
            except Exception as e:
                print(f"Error sending to {chat_id}: {e}")
        
        tracker.save_current_state(current_tracks)


def main():
    """Start the bot"""
    try:
        print("Starting web server...")
        threading.Thread(target=run_web, daemon=True).start()
        print("✅ Web server started")
        
        if not BOT_TOKEN:
            print("❌ ERROR: BOT_TOKEN not set!")
            return
        
        if not os.path.exists("browser.json"):
            print("❌ ERROR: browser.json not found!")
            return
        
        print("Initializing bot...")
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("setplaylist", setplaylist))
        app.add_handler(CommandHandler("reset", reset))
        app.add_handler(CommandHandler("check", check_playlist))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CallbackQueryHandler(button_callback))
        
        if app.job_queue:
            app.job_queue.run_repeating(periodic_check, interval=CHECK_INTERVAL, first=10)
            print(f"✅ Bot started! Checking every {CHECK_INTERVAL} seconds")
        
        print("Starting polling...")
        app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("="*50)
    print("YouTube Music Playlist Tracker Bot")
    print("="*50)
    main()
