from wiki import get_page, find_short_path, set_hard_mode
import random
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

def main():
    print("\n\n🥓 Welcome to WikiBacon! 🥓\n")
    print("In this game, we start from a random Wikipedia page, and then we compete to see who can name a page that is *farthest away* from the original page.\n")
    print("\nDifficulty modes:")
    print("  [1] Normal - Uses both links and categories")
    print("  [2] Hard - Links only (no categories)")
    mode = input("Choose mode (1 or 2, default=1): ").strip()
    
    if mode == "2":
        set_hard_mode(True)
        print("🔥 Hard mode activated! Categories disabled.\n")
    else:
        set_hard_mode(False)
        print("✨ Normal mode selected.\n")
    
    print("Ready to play? Hit Enter to start, or type 'q' to quit")
    cmd = input()
    if cmd == "q":
        return
    
    with open("dictionary.txt", "r") as f:
        common_words = f.read().splitlines()

    # Removed random.seed(42) to fix bias towards Python page

    while True:
        # Get start page - retry if not found
        start_page = None
        while not start_page:
            start_word = random.choice(common_words)
            start_page = get_page(start_word)
        
        print(f"The starting page is: {start_page.title}\n")
        print(f"Summary: {start_page.summary[:500]}...\n")

        # Get computer's page - retry if not found
        computer_page = None
        while not computer_page:
            computer_word = random.choice(common_words)
            computer_page = get_page(computer_word)

        print(f"The computer's page is: {computer_page.title}\n")
        print(f"Summary: {computer_page.summary[:500]}...\n")

        # Get user's page - allow retry if not found
        user_page = None
        while not user_page:
            print("What would you like your page to be?")
            user_page_name = input()
            user_page = get_page(user_page_name)
            if not user_page:
                print(f"Could not find page '{user_page_name}'. Please try another page.\n")
        
        print(f"Your page is: {user_page.title}\n")
        print(f"Summary: {user_page.summary[:500]}...\n")

        print("Calculating Bacon paths...\n")

        computer_path = find_short_path(start_page, computer_page)
        print("Computer's path:")
        if computer_path:
            print(f"\n -> ".join(computer_path))
            print(f"Length: {len(computer_path)}\n")
            computer_score = len(computer_path)
        else:
            print("No path found (or search timed out).")
            print("Length: ∞ (Infinite)\n")
            computer_score = 100 # Max score for unconnected/hard-to-reach pages

        user_path = find_short_path(start_page, user_page)
        print("Your path:")
        if user_path:
            print(f"\n -> ".join(user_path))
            print(f"Length: {len(user_path)}\n")
            user_score = len(user_path)
        else:
            print("No path found (or search timed out).")
            print("Length: ∞ (Infinite)\n")
            user_score = 100 # Max score for unconnected/hard-to-reach pages

        if computer_score > user_score:
            print("I win!")
        elif computer_score < user_score:
            print("You win!")
        else:
            print("It's a tie!")

        print("\n\nPlay again? Hit Enter for another round, or type 'q' to quit")
        cmd = input()
        if cmd == "q":
            print("\n🥓 Thanks for playing! 🥓\n")
            print("WikiBacon is not affiliated with Wikipedia or the Wikimedia Foundation. To donate to Wikipedia and support their vision of an open internet that makes games like this possible, please visit https://donate.wikimedia.org/\n")
            return

if __name__ == "__main__":
    main()
