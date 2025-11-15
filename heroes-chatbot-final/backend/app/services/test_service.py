def match_guru(answers):
    total = sum(answers)
    if total < 10:
        return "buffett"
    elif total < 20:
        return "dalio"
    else:
        return "lynch"
