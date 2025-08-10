# setup_web_interface.py
"""
Setup script to add web interface to your existing Hyperliquid bot
"""

import os
import sys
import subprocess

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing required dependencies...")
    
    requirements = [
        'websockets>=11.0.3',
        'numpy>=1.24.0'
    ]
    
    for package in requirements:
        try:
            print(f"   Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            print(f"   ✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Failed to install {package}: {e}")
            return False
    
    return True

def create_web_interface_files():
    """Create the web interface files"""
    print("📁 Creating web interface files...")
    
    # The web_interface.py content (from the artifacts above)
    web_interface_content = '''# This file contains the web interface code
# Copy the content from the web_interface artifact above
'''
    
    # Create web_interface.py if it doesn't exist
    if not os.path.exists('web_interface.py'):
        print("   Creating web_interface.py...")
        print("   ⚠️  Please copy the web_interface.py content from the artifacts above")
        with open('web_interface.py', 'w') as f:
            f.write("# Please copy the web_interface.py content from the artifacts\n")
    else:
        print("   ✅ web_interface.py already exists")
    
    # Create main_with_web.py
    if not os.path.exists('main_with_web.py'):
        print("   Creating main_with_web.py...")
        print("   ⚠️  Please copy the main_with_web.py content from the artifacts above")
        with open('main_with_web.py', 'w') as f:
            f.write("# Please copy the main_with_web.py content from the artifacts\n")
    else:
        print("   ✅ main_with_web.py already exists")

def backup_original_main():
    """Backup the original main.py file"""
    if os.path.exists('main.py') and not os.path.exists('main_original.py'):
        print("💾 Backing up original main.py to main_original.py...")
        os.rename('main.py', 'main_original.py')
        print("   ✅ Backup created")

def show_instructions():
    """Show setup instructions"""
    print("\n" + "=" * 60)
    print("🚀 WEB INTERFACE SETUP INSTRUCTIONS")
    print("=" * 60)
    
    print("\n1. 📋 COPY THE FILES:")
    print("   - Copy web_interface.py content from the first artifact")
    print("   - Copy main_with_web.py content from the second artifact")
    print("   - Both files should be in your project directory")
    
    print("\n2. 🔧 MODIFY YOUR EXISTING CODE:")
    print("   - Your original main.py has been backed up to main_original.py")
    print("   - Use main_with_web.py as your new main file")
    
    print("\n3. 🚀 RUN THE BOT:")
    print("   python main_with_web.py")
    
    print("\n4. 🌐 OPEN THE DASHBOARD:")
    print("   Open your browser to: http://localhost:8000/dashboard.html")
    
    print("\n5. 📊 FEATURES:")
    print("   ✅ Real-time price and orderbook display")
    print("   ✅ Live microstructure metrics")
    print("   ✅ AI-generated market analysis")
    print("   ✅ Account and position tracking")
    print("   ✅ Open orders monitoring")
    print("   ✅ Professional trading interface")
    
    print("\n6. 🔌 WEBSOCKET CONNECTION:")
    print("   The dashboard connects to ws://localhost:8765")
    print("   This is automatically started by the bot")
    
    print("\n⚠️  IMPORTANT NOTES:")
    print("   - The web interface runs alongside your existing bot")
    print("   - All original functionality is preserved")
    print("   - The dashboard is read-only (no trading controls for safety)")
    print("   - Real-time updates happen automatically")
    
    print("\n" + "=" * 60)

def main():
    """Main setup function"""
    print("🚀 Setting up Hyperliquid Market Maker Web Interface")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('config.py'):
        print("❌ config.py not found. Please run this script in your bot directory.")
        return False
    
    print("✅ Found config.py - proceeding with setup...")
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies")
        return False
    
    # Backup original files
    backup_original_main()
    
    # Create web interface files
    create_web_interface_files()
    
    # Show instructions
    show_instructions()
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Setup preparation complete!")
        print("📋 Please follow the instructions above to complete the setup.")
    else:
        print("\n❌ Setup failed. Please check the errors above.")