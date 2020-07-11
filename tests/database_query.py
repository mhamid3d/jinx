import mongorm


db = mongorm.getHandler()
filter = mongorm.getFilter()




# filter.search(db['stalk'], job="GARB", version=1)
filter.search(db['stalk'], job="GARB")

twig = db['stalk'].all(filter)

object1 = twig[0]