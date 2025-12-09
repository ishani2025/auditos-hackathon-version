from services.detect_screen import screen_detector

def main():
    image_path = "images/trashpica.jpeg"
    print(f"🔎 Running screen detection on: {image_path}")
    
    result = screen_detector.detect(image_path)
    
    print("\nResult:")
    for key, value in result.items():
        print(f"{key}: {value}")

if __name__ == "__main__":
    main()
