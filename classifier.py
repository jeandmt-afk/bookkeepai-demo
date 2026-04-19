def classify_transaction(description: str):
    text = description.lower()

    # PERSONAL DETECTION FIRST
    personal_keywords = [
        "family", "personal", "home", "wife", "kids", "dinner", "birthday"
    ]

    for word in personal_keywords:
        if word in text:
            return "Personal", "Needs Review", "Personal"

    # OUTGOING PAYMENT CHECK
    if "sent" in text or "transfer" in text:
        return "Expense", "Needs Review", "Review"

    # CATEGORY KEYWORDS
    categories = {
        "Cost of Goods": [
            "supplier", "restock", "wholesale", "bulk", "inventory", "stock",
            "delivery", "market", "farm", "chicken", "vegetable", "rice",
            "noodles", "canned", "eggs", "bread", "distributor"
        ],
        "Income": ["invoice", "sale", "client", "revenue", "cash", "gcash", "customer", "order"],
        "Transportation": ["uber", "fuel", "gas", "taxi", "grab", "truck", "tricycle"],
        "Marketing": ["ads", "marketing", "facebook", "google", "promotion", "flyers", "banner", "tarpaulin", "signage"],
        "Office Supplies": ["office", "printer", "paper", "staples", "ink"],
        "Software & Subscriptions": ["subscription", "software", "saas", "canva", "chatgpt"],
        "Meals & Entertainment": ["restaurant", "food", "lunch", "coffee"],
        "Utilities": ["electric", "water", "internet", "wifi", "bill", "pos"],
        "Rent": ["rent"],
        "Travel": ["hotel", "flight", "airbnb", "bus", "trip"],
        "Equipment": ["laptop", "computer", "equipment", "tools", "phone"],
        "Salary": ["salary", "payroll", "wages", "helper", "guard"],
        "Bank Fees": ["bank fee", "charge", "service fee"],
        "Tax": ["tax", "vat"]
    }

    scores = {}

    for category, keywords in categories.items():
        score = 0
        for word in keywords:
            if word in text:
                score += 1
        if score > 0:
            scores[category] = score

    if scores:
        priority_order = [
            "Meals & Entertainment",
            "Travel",
            "Transportation",
            "Cost of Goods",
            "Equipment",
            "Office Supplies",
            "Marketing",
            "Software & Subscriptions",
            "Utilities",
            "Rent",
            "Salary",
            "Bank Fees",
            "Tax",
            "Income"
        ]

        best_category = None

        for category in priority_order:
            if category in scores:
                best_category = category
                break

        if best_category is None:
            return "Uncategorized", "Needs Review", "Review"

        if scores[best_category] > 1:
            return best_category, "Smart AI", "Business"
        else:
            return best_category, "Low Confidence", "Review"

    return "Uncategorized", "Needs Review", "Review"