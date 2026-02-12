#!/bin/bash

# LeetCode to Notion Sync Service Setup Script
# This script manages the launchd service for automatic syncing

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_FILE="$SCRIPT_DIR/com.user.leetcode_notion_sync.plist"
LABEL="com.user.leetcode_notion_sync"
PLIST_PATH="$HOME/Library/LaunchAgents/com.user.leetcode_notion_sync.plist"
LOG_DIR="$HOME/Library/Logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
check_macos() {
    if [[ "$OSTYPE" != "darwin"* ]]; then
        echo_error "This script only works on macOS!"
        exit 1
    fi
}

# Create necessary directories
setup_directories() {
    echo_status "Creating directories..."
    mkdir -p "$LOG_DIR"
}

# Install the service
install() {
    echo_status "Installing LeetCode to Notion sync service..."
    
    check_macos
    setup_directories
    
    # Check if plist exists
    if [[ ! -f "$PLIST_FILE" ]]; then
        echo_error "Plist file not found: $PLIST_FILE"
        exit 1
    fi
    
    # Copy plist to LaunchAgents directory
    cp "$PLIST_FILE" "$PLIST_PATH"
    echo_status "Copied plist to $PLIST_PATH"
    
    # Load the service
    launchctl load "$PLIST_PATH" 2>/dev/null || true
    echo_status "Service loaded successfully!"
    
    echo ""
    echo_status "✅ Installation complete!"
    echo "   - Service is now running in the background"
    echo "   - Will sync every 30 minutes (configurable in plist)"
    echo "   - Logs: $LOG_DIR/leetcode_notion_sync.log"
    echo ""
    echo "Useful commands:"
    echo "   $0 status    - Check if service is running"
    echo "   $0 logs      - View recent logs"
    echo "   $0 start     - Start the service"
    echo "   $0 stop      - Stop the service"
    echo "   $0 uninstall - Remove the service"
}

# Uninstall the service
uninstall() {
    echo_status "Uninstalling LeetCode to Notion sync service..."
    
    check_macos
    
    # Unload if loaded
    if launchctl list | grep -q "$LABEL"; then
        launchctl unload "$PLIST_PATH" 2>/dev/null || true
        echo_status "Service unloaded"
    fi
    
    # Remove plist
    if [[ -f "$PLIST_PATH" ]]; then
        rm "$PLIST_PATH"
        echo_status "Removed plist file"
    fi
    
    echo ""
    echo_status "✅ Uninstallation complete!"
}

# Start the service
start() {
    echo_status "Starting service..."
    check_macos
    
    if [[ ! -f "$PLIST_PATH" ]]; then
        echo_error "Service not installed. Run: $0 install"
        exit 1
    fi
    
    launchctl start "$LABEL"
    echo_status "Service started!"
}

# Stop the service
stop() {
    echo_status "Stopping service..."
    check_macos
    launchctl stop "$LABEL"
    echo_status "Service stopped!"
}

# Restart the service
restart() {
    echo_status "Restarting service..."
    stop
    sleep 2
    start
    echo_status "Service restarted!"
}

# Check service status
status() {
    echo_status "Checking service status..."
    check_macos
    
    if launchctl list | grep -q "$LABEL"; then
        echo -e "${GREEN}[RUNNING]${NC} Service is running"
        
        # Show last run info
        echo ""
        echo "Recent activity:"
        launchctl list | grep "$LABEL" || true
        
        # Show log tail
        if [[ -f "$LOG_DIR/leetcode_notion_sync.log" ]]; then
            echo ""
            echo "Recent logs (last 10 lines):"
            tail -10 "$LOG_DIR/leetcode_notion_sync.log" 2>/dev/null || echo "No logs yet"
        fi
    else
        echo_warn "Service is not running"
        echo "Run '$0 install' to set up the service"
    fi
}

# View logs
logs() {
    echo_status "Showing logs (Ctrl+C to exit)..."
    
    if [[ -f "$LOG_DIR/leetcode_notion_sync.log" ]]; then
        tail -f "$LOG_DIR/leetcode_notion_sync.log"
    else
        echo_error "Log file not found: $LOG_DIR/leetcode_notion_sync.log"
        echo "The service may not have run yet. Wait for the first sync cycle."
    fi
}

# Run manually once
run_now() {
    echo_status "Running sync manually..."
    cd "$SCRIPT_DIR"
    python3 main.py
    echo_status "Manual sync complete!"
}

# Help message
show_help() {
    echo "LeetCode to Notion Sync Service Manager"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "   install   - Install and start the background service"
    echo "   uninstall - Stop and remove the background service"
    echo "   start     - Start the service"
    echo "   stop      - Stop the service"
    echo "   restart   - Restart the service"
    echo "   status    - Check if service is running"
    echo "   logs      - View live logs (tail -f)"
    echo "   run       - Run sync manually once"
    echo "   help      - Show this help message"
    echo ""
    echo "Service configuration:"
    echo "   Interval: Every 30 minutes"
    echo "   Logs: ~/Library/Logs/leetcode_notion_sync.log"
    echo ""
}

# Main
case "${1:-help}" in
    install)
        install
        ;;
    uninstall)
        uninstall
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    run)
        run_now
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
