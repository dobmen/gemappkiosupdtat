import 'dart:ui';
import 'package:flutter/material.dart';

void main() {
  runApp(const KioskOS());
}

class KioskOS extends StatelessWidget {
  const KioskOS({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: Colors.black,
        fontFamily: 'Inter',
      ),
      home: const DesktopScreen(),
    );
  }
}

class DesktopScreen extends StatefulWidget {
  const DesktopScreen({Key? key}) : super(key: key);

  @override
  State<DesktopScreen> createState() => _DesktopScreenState();
}

class _DesktopScreenState extends State<DesktopScreen> {
  bool _isControlCenterOpen = false;
  bool _isNotificationOpen = false;

  void _toggleControlCenter() {
    setState(() {
      _isControlCenterOpen = !_isControlCenterOpen;
      if (_isControlCenterOpen) _isNotificationOpen = false;
    });
  }

  void _toggleNotificationCenter() {
    setState(() {
      _isNotificationOpen = !_isNotificationOpen;
      if (_isNotificationOpen) _isControlCenterOpen = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      body: Stack(
        children: [
          // 1. Vibrant Wallpaper to show off blur
          Container(
            decoration: const BoxDecoration(
              gradient: RadialGradient(
                colors: [Color(0xFF5A28FF), Color(0xFF101018)],
                center: Alignment(-0.5, -0.5),
                radius: 1.5,
              ),
            ),
          ),
          
          Container(
            decoration: const BoxDecoration(
              gradient: RadialGradient(
                colors: [Color(0x8828C8FF), Colors.transparent],
                center: Alignment(0.8, 0.8),
                radius: 1.0,
              ),
            ),
          ),

          // 2. Desktop Content
          Column(
            children: [
              // Status Bar (Clickable to open Control Center)
              GestureDetector(
                onTap: _toggleControlCenter,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 40.0, vertical: 20.0),
                  color: Colors.transparent, // Catch taps
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text("🌤️ 72° Sunny", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      
                      // Notification Trigger
                      GestureDetector(
                        onTap: () {
                          _toggleNotificationCenter();
                        },
                        child: Container(
                          padding: const EdgeInsets.all(8.0),
                          color: Colors.transparent,
                          child: const Text("🔔 3   📶  🔋 100%", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const Spacer(),

              // Clock Widget
              Column(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Text("12:00", style: TextStyle(fontSize: 140, fontWeight: FontWeight.bold, height: 1.0, letterSpacing: -4)),
                  Text("Monday, January 1", style: TextStyle(fontSize: 28, color: Colors.white70)),
                ],
              ),

              const Spacer(),

              // App Dock (Glassmorphism)
              ClipRRect(
                borderRadius: BorderRadius.circular(45),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 35, sigmaY: 35),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 20),
                    margin: const EdgeInsets.only(bottom: 40),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      border: Border.all(color: Colors.white.withOpacity(0.15)),
                      borderRadius: BorderRadius.circular(45),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 40, offset: const Offset(0, 10)),
                      ]
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        _buildDockIcon(const Color(0xFF1DB954), "🎵"),
                        const SizedBox(width: 25),
                        _buildDockIcon(const Color(0xFFFF0000), "▶️"),
                        const SizedBox(width: 25),
                        _buildDockIcon(const Color(0xFF2D9CDB), "🌤️"),
                        const SizedBox(width: 25),
                        _buildDockIcon(const Color(0xFFF2994A), "⚙️"),
                        const SizedBox(width: 25),
                        _buildDockIcon(const Color(0xFF8E44AD), "📸"),
                      ],
                    ),
                  ),
                ),
              )
            ],
          ),

          // 3. Control Center Overlay (Slides from top)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 500),
            curve: Curves.fastOutSlowIn,
            top: _isControlCenterOpen ? 40 : -size.height,
            left: size.width * 0.1,
            right: size.width * 0.1,
            height: size.height * 0.6,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(40),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 45, sigmaY: 45),
                child: Container(
                  padding: const EdgeInsets.all(40),
                  decoration: BoxDecoration(
                    color: const Color(0xFF14141C).withOpacity(0.5),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                    borderRadius: BorderRadius.circular(40),
                  ),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Control Center", style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold)),
                          IconButton(
                            icon: const Icon(Icons.close, color: Colors.white, size: 30),
                            onPressed: _toggleControlCenter,
                          )
                        ],
                      ),
                      const SizedBox(height: 30),
                      Row(
                        children: [
                          Expanded(child: _buildCcCard("📶", "Wi-Fi", "Connected", Colors.blue)),
                          const SizedBox(width: 20),
                          Expanded(child: _buildCcCard("ᛒ", "Bluetooth", "On", Colors.white12)),
                        ],
                      ),
                      const SizedBox(height: 20),
                      _buildSliderCard("🔆 Brightness", 0.8),
                      const SizedBox(height: 20),
                      _buildSliderCard("🔊 Volume", 0.5),
                    ],
                  ),
                 ),
                ),
              ),
            ),
          ),

          // 4. Notification Center Overlay (Slides from right)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 500),
            curve: Curves.fastOutSlowIn,
            top: 40,
            bottom: 40,
            right: _isNotificationOpen ? 20 : -450,
            width: 400,
            child: ClipRRect(
              borderRadius: BorderRadius.circular(40),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 45, sigmaY: 45),
                child: Container(
                  padding: const EdgeInsets.all(30),
                  decoration: BoxDecoration(
                    color: const Color(0xFF14141C).withOpacity(0.5),
                    border: Border.all(color: Colors.white.withOpacity(0.1)),
                    borderRadius: BorderRadius.circular(40),
                  ),
                  child: SingleChildScrollView(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text("Notifications", style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                          IconButton(
                            icon: const Icon(Icons.close, color: Colors.white),
                            onPressed: _toggleNotificationCenter,
                          )
                        ],
                      ),
                      const SizedBox(height: 20),
                      _buildNotifCard("💬 Messages", "New message from John"),
                      _buildNotifCard("🌤️ Weather Alert", "Rain starting in 20 minutes."),
                      _buildNotifCard("🎵 Spotify", "New Weekly Discovery playlist is ready!"),
                    ],
                  ),
                 ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDockIcon(Color color, String emoji) {
    return Container(
      width: 75,
      height: 75,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(20),
        boxShadow: const [
          BoxShadow(color: Colors.black45, blurRadius: 10, offset: Offset(0, 5)),
        ],
      ),
      child: Center(
        child: Text(emoji, style: const TextStyle(fontSize: 36)),
      ),
    );
  }

  Widget _buildCcCard(String emoji, String title, String subtitle, Color bgColor) {
    return Container(
      padding: const EdgeInsets.all(25),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text("$emoji  $title", style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 5),
          Text(subtitle, style: const TextStyle(fontSize: 16, color: Colors.white70)),
        ],
      ),
    );
  }

  Widget _buildSliderCard(String title, double val) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 25, vertical: 15),
      decoration: BoxDecoration(
        color: Colors.white12,
        borderRadius: BorderRadius.circular(25),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white)),
          Slider(
            value: val,
            onChanged: (v) {},
            activeColor: Colors.white,
            inactiveColor: Colors.white24,
          )
        ],
      ),
    );
  }

  Widget _buildNotifCard(String title, String body) {
    return Container(
      margin: const EdgeInsets.only(bottom: 15),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white12,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 5),
          Text(body, style: const TextStyle(fontSize: 14, color: Colors.white70)),
        ],
      ),
    );
  }
}
