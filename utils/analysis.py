def get_vibe(score):
    if not isinstance(score, (int, float)):
        return "unknown"
    if score>4.5 and score<=5:
        return "Excited"
    elif score>3.5 and score<=4.5:
        return "Happy"
    elif score>2.5 and score<=3.5:
        return "Okay"
    elif score>1.5 and score<=2.5:
        return "Sad"
    elif score>=0 and score<=1.5:
        return "Frustated"