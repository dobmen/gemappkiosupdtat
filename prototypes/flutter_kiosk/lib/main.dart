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
      theme: ThemeData.dark().copyWith(
        scaffoldBackgroundColor: Colors.black,
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
  bool _isAppOpen = false;

  void _toggleApp() {
    setState(() {
      _isAppOpen = !_isAppOpen;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // 1. Wallpaper
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF1E1E38), Color(0xFF0D0D1A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
          ),

          // 2. Desktop Content
          Column(
            children: [
              // Status Bar
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 40.0, vertical: 20.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: const [
                    Text("🌤️ 72° Sunny", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text("📶  🔋 100%", style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                  ],
                ),
              ),

              const Spacer(),

              // Clock Widget (Glassmorphism)
              ClipRRect(
                borderRadius: BorderRadius.circular(40),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 25, sigmaY: 25),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 80, vertical: 40),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.1),
                      border: Border.all(color: Colors.white.withOpacity(0.2)),
                      borderRadius: BorderRadius.circular(40),
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: const [
                        Text("12:00", style: TextStyle(fontSize: 120, fontWeight: FontWeight.bold, height: 1.0)),
                        Text("Monday, January 1", style: TextStyle(fontSize: 24, color: Colors.white70)),
                      ],
                    ),
                  ),
                ),
              ),

              const Spacer(),

              // App Dock
              Container(
                margin: const EdgeInsets.only(bottom: 40),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    _buildDockIcon(Colors.green, "🎵"),
                    const SizedBox(width: 30),
                    _buildDockIcon(Colors.red, "▶️"),
                    const SizedBox(width: 30),
                    _buildDockIcon(Colors.blue, "🌤️"),
                    const SizedBox(width: 30),
                    _buildDockIcon(Colors.orange, "⚙️"),
                  ],
                ),
              )
            ],
          ),

          // 3. App Overlay (Animated smoothly using Implicit Animations)
          AnimatedPositioned(
            duration: const Duration(milliseconds: 400),
            curve: Curves.fastOutSlowIn,
            top: _isAppOpen ? 0 : MediaQuery.of(context).size.height,
            bottom: 0,
            left: 0,
            right: 0,
            child: AnimatedOpacity(
              duration: const Duration(milliseconds: 300),
              opacity: _isAppOpen ? 1.0 : 0.0,
              child: ClipRRect(
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 40, sigmaY: 40),
                  child: Container(
                    color: Colors.black.withOpacity(0.6),
                    child: Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(30.0),
                          child: Row(
                            children: [
                              TextButton(
                                onPressed: _toggleApp,
                                style: TextButton.styleFrom(
                                  backgroundColor: Colors.white12,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                                  padding: const EdgeInsets.symmetric(horizontal: 30, vertical: 15),
                                ),
                                child: const Text("✕ Close", style: TextStyle(color: Colors.white, fontSize: 18)),
                              ),
                            ],
                          ),
                        ),
                        Expanded(
                          child: Container(
                            margin: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: Colors.white.withOpacity(0.05),
                              borderRadius: BorderRadius.circular(40),
                              border: Border.all(color: Colors.white12),
                            ),
                            child: const Center(
                              child: Text(
                                "Native 60fps Flutter UI!",
                                style: TextStyle(fontSize: 24, color: Colors.white),
                              ),
                            ),
                          ),
                        )
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
    return GestureDetector(
      onTap: _toggleApp,
      child: Container(
        width: 80,
        height: 80,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(color: Colors.black45, blurRadius: 10, offset: const Offset(0, 5)),
          ],
        ),
        child: Center(
          child: Text(emoji, style: const TextStyle(fontSize: 40)),
        ),
      ),
    );
  }
}
