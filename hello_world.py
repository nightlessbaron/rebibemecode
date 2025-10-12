#!/usr/bin/env python3
"""
Simple Hello World program for Daytona
"""

def main():
    print("Hello, World!")
    print("This is running on Daytona!")
    print("Current time:", __import__('datetime').datetime.now())

if __name__ == "__main__":
    main()