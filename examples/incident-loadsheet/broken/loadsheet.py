# broken/loadsheet.py — the incident, reconstructed. A check-in system builds
# a load sheet from standard passenger weights. Where the booking record has no
# category, the category is guessed from the passenger's honorific — and the
# mapping encodes a convention under which "Miss" means a child. Three adult
# passengers are counted at child weight. The arithmetic is correct, the sheet
# is tidy, and the total is wrong with no signal anywhere.
# Run: python3 broken/loadsheet.py

# Judgment calls buried as constants: the standard weights and the honorific
# convention are both priors, invisible to every consumer of the total.
STANDARD_WEIGHT_KG = {"adult": 84, "child": 35}
TITLE_CATEGORY = {"Mr": "adult", "Mrs": "adult", "Ms": "adult",
                  "Miss": "child", "Master": "child"}

# (seat, title, booked category or None — None means the upgraded system must guess)
MANIFEST = [
    ("1A", "Mr",   "adult"),
    ("1B", "Mrs",  "adult"),
    ("2A", "Ms",   "adult"),
    ("2B", "Mr",   "adult"),
    ("3A", "Miss", None),
    ("3B", "Mr",   "adult"),
    ("4A", "Miss", None),
    ("4B", "Mrs",  "adult"),
    ("5A", "Miss", None),
    ("5B", "Mr",   "adult"),
]


def categorize(title, booked_category):
    if booked_category is not None:
        return booked_category
    return TITLE_CATEGORY[title]


def main():
    print("load sheet — flight PL123:")
    total = 0
    for seat, title, booked in MANIFEST:
        category = categorize(title, booked)
        weight = STANDARD_WEIGHT_KG[category]
        total += weight
        print(f"  {seat}  {title:<6} {category:<6} {weight} kg")
    print(f"total takeoff mass: {total} kg")
    print("load sheet: complete")


if __name__ == "__main__":
    main()
