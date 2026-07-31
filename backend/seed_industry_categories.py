"""
FoodTrack -- Food Industry Category Seed (150+ items, 13 new categories)

Adds new food-industry categories and items to the existing Food Kingdom
taxonomy, expanding coverage toward a full food-industry map (30+ categories).
Each item carries full taxonomic metadata (phylum, family, genus, class,
order, local names, uses) following the seed_food_items / seed_more_items
conventions.
"""
import asyncio, sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, func

from app.database import async_session, engine, Base
from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

INDUSTRY_CATEGORIES = {
    "BEVERAGES": {
        "code": "BEVERAGES", "description": "Non-alcoholic beverages and juices",
        "items": [
            ("ORANGE-JUICE", "Orange Juice", "Citrus × sinensis", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "8-10 months", "Cold-pressed juice; breakfast beverage; rich in Vitamin C"),
            ("APPLE-JUICE", "Apple Juice", "Malus domestica", "Malus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Clarified or cloudy juice; children's favorite; cider base"),
            ("GRAPE-JUICE", "Grape Juice", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Purple or white unfermented must; concentrate export"),
            ("TOMATO-JUICE", "Tomato Juice", "Solanum lycopersicum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Savory juice; Bloody Mary base; canned concentrate"),
            ("PINEAPPLE-JUICE", "Pineapple Juice", "Ananas comosus", "Ananas", "Magnoliophyta", "Liliopsida", "Poales", "Bromeliaceae", "18-24 months", "Tropical juice; smoothie base; canned and fresh"),
            ("CRANBERRY-JUICE", "Cranberry Juice", "Vaccinium macrocarpon", "Vaccinium", "Magnoliophyta", "Magnoliopsida", "Ericales", "Ericaceae", "3-5 months", "Tart juice; usually blended; urinary health beverage"),
            ("COLA", "Cola Beverage", "Cola acuminata", "Cola", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "6-8 months", "Carbonated soft drink; kola nut flavor; caramel color"),
            ("GINGER-ALE", "Ginger Ale", "Zingiber officinale", "Zingiber", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "8-10 months", "Carbonated ginger drink; golden ginger ale; cocktail mixer"),
            ("ICED-TEA", "Iced Tea", "Camellia sinensis", "Camellia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Theaceae", "24-36 months", "Chilled brewed tea; lemon/peach variants; ready-to-drink"),
            ("MANGO-NECTAR", "Mango Nectar", "Mangifera indica", "Mangifera", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "4-5 months", "Thick fruit nectar; puree-based; tropical breakfast drink"),
            ("TAMARIND-DRINK", "Tamarind Cooler", "Tamarindus indica", "Tamarindus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "6-7 months", "Refreshing tangy drink; Mexico and South Asia; concentrate"),
            ("CARROT-JUICE", "Carrot Juice", "Daucus carota subsp. sativus", "Daucus", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Nutrient-dense juice; beta-carotene; blended drinks"),
        ]
    },
    "PLANT_DAIRY": {
        "code": "PLANT_DAIRY", "description": "Plant-based dairy alternatives",
        "items": [
            ("OAT-MILK", "Oat Milk", "Avena sativa", "Avena", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "5-7 months", "Barista oat milk; creamy; coffee culture favorite"),
            ("SOY-MILK", "Soy Milk", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Classic plant milk; high protein; tofu base"),
            ("ALMOND-MILK", "Almond Milk", "Prunus dulcis", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "5-6 months", "Low-calorie nut milk; sweetened or unsweetened"),
            ("COCONUT-MILK", "Coconut Milk", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Canned or drinking coconut milk; curries, smoothies"),
            ("CASHEW-MILK", "Cashew Milk", "Anacardium occidentale", "Anacardium", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "6-8 months", "Creamy nut milk; lower calories; barista blends"),
            ("RICE-MILK", "Rice Milk", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Naturally sweet; hypoallergenic; low fat"),
            ("PEA-MILK", "Pea Milk", "Pisum sativum", "Pisum", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "High-protein plant milk; neutral flavor; complete protein"),
            ("COCONUT-YOGURT", "Coconut Yogurt", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Cultured coconut base; dairy-free probiotic"),
            ("SOY-YOGURT", "Soy Yogurt", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Cultured soy; Greek-style options; protein-rich"),
            ("OAT-YOGURT", "Oat Yogurt", "Avena sativa", "Avena", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "5-7 months", "Fermented oat base; creamy; grain-based alternative"),
            ("VEGAN-BUTTER", "Vegan Butter (Margarine)", "Helianthus annuus", "Helianthus", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Plant oil spread; sunflower/coconut oil base; baking fat"),
            ("VEGAN-CHEESE", "Vegan Cheese", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Cultured nut/coconut cheese; shreds and blocks; melting blends"),
        ]
    },
    "CONFECTIONERY": {
        "code": "CONFECTIONERY", "description": "Confectionery and sweets",
        "items": [
            ("CHOCOLATE-MILK", "Milk Chocolate", "Theobroma cacao", "Theobroma", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "36-48 months", "Cocoa plus milk solids; bars and filled; global favorite"),
            ("CHOCOLATE-DARK", "Dark Chocolate", "Theobroma cacao", "Theobroma", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "36-48 months", "High cocoa percentage; antioxidant flavanols; 70-90% bars"),
            ("CHOCOLATE-WHITE", "White Chocolate", "Theobroma cacao", "Theobroma", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "36-48 months", "Cocoa butter with sugar and milk; no cocoa solids"),
            ("COCOA-BUTTER", "Cocoa Butter", "Theobroma cacao", "Theobroma", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "36-48 months", "Pressed cocoa fat; chocolate texture; cosmetics"),
            ("NOUGAT", "Nougat", "Prunus dulcis", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "5-6 months", "Sugar-honey-almond confection; Montélimar; soft or hard"),
            ("FUDGE", "Fudge", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Sugar-butter-milk confection; soft crystalline texture"),
            ("TOFFEE", "Toffee", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Butter-sugar caramel; hard brittle; English classic"),
            ("CARAMEL", "Caramel", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Heated sugar syrup; sauce, candy and filling"),
            ("LICORICE", "Licorice Candy", "Glycyrrhiza glabra", "Glycyrrhiza", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "24-36 months", "Root-extract candy; salty black or red twists"),
            ("MARSHMALLOW", "Marshmallow", "Althaea officinalis", "Althaea", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "4-5 months", "Sugar-gelatin foam; s'mores and hot cocoa topping"),
            ("HALVA", "Halva (Sesame)", "Sesamum indicum", "Sesamum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Pedaliaceae", "3-4 months", "Tahini-sugar confection; Middle Eastern crumbly sweet"),
            ("TURKISH-DELIGHT", "Turkish Delight (Lokum)", "Rosa × damascena", "Rosa", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Starch-sugar gel; rose or pistachio; dusted with icing sugar"),
            ("GUMMY-CANDY", "Gummy Candy", "Citrus aurantium", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "6-8 months", "Gelatin or pectin chews; fruit flavors; bear shapes"),
        ]
    },
    "BAKERY": {
        "code": "BAKERY", "description": "Bakery products and pastries",
        "items": [
            ("BAGUETTE", "Baguette", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "French crusty loaf; crackling crust; daily bread"),
            ("SOURDOUGH-BREAD", "Sourdough Bread", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Wild yeast leaven; tangy; artisan staple"),
            ("CROISSANT", "Croissant", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Laminated pastry; butter layers; French breakfast"),
            ("BAGEL", "Bagel", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Boiled then baked ring; New York style; varied toppings"),
            ("BRIOCHE", "Brioche", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Enriched butter bread; soft crumb; French Viennoiserie"),
            ("CIABATTA", "Ciabatta", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Italian open-crumb loaf; olive oil; panini base"),
            ("PITA", "Pita Bread", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Pocket flatbread; Middle Eastern; wraps and dips"),
            ("NAAN", "Naan", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Tandoor flatbread; yogurt leavened; garlic and butter"),
            ("TORTILLA-FLOUR", "Flour Tortilla", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Wheat flatbread; wraps and burritos; Mexican-American staple"),
            ("FOCACCIA", "Focaccia", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Italian flat oven bread; olive oil dimples; rosemary"),
            ("RYE-BREAD", "Rye Bread", "Secale cereale", "Secale", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Dense dark bread; pumpernickel; Scandinavian staple"),
            ("CRUMPET", "Crumpet", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Griddle-cooked round; honeycomb holes; British tea time"),
        ]
    },
    "SNACKS": {
        "code": "SNACKS", "description": "Savory snack foods",
        "items": [
            ("POTATO-CHIP", "Potato Chip", "Solanum tuberosum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Sliced fried potatoes; salted and flavored; classic snack"),
            ("CORN-CHIP", "Corn Chip", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Fried corn strips; salty; dip companion"),
            ("TORTILLA-CHIP", "Tortilla Chip", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Triangular fried corn; salsa and guacamole companion"),
            ("POPCORN", "Popcorn", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Popped kernel snack; movie butter, kettle, caramel"),
            ("PRETZEL", "Pretzel", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Baked twisted dough; salted; soft or hard"),
            ("CRACKER", "Cracker", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Dry crisp biscuit; saltine, water and cheese crackers"),
            ("RICE-CRACKER", "Rice Cracker (Senbei)", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Japanese rice cracker; soy glaze; nori wrapped"),
            ("PITA-CHIP", "Pita Chip", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "7-9 months", "Baked pita wedges; seasoned; hummus pairing"),
            ("GRANOLA-BAR", "Granola Bar", "Avena sativa", "Avena", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "5-7 months", "Baked oat bar; honey and chocolate; on-the-go breakfast"),
            ("PROTEIN-BAR", "Protein Bar", "Pisum sativum", "Pisum", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "High-protein snack; pea and whey blends; fitness"),
            ("TRAIL-MIX", "Trail Mix", "Arachis hypogaea", "Arachis", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Nuts, seeds and dried fruit blend; hiking snack"),
            ("PORK-RIND", "Pork Rind (Chicharrones)", "Sus scrofa domesticus", "Sus", "Chordata", "Mammalia", "Artiodactyla", "Suidae", "5-7 months", "Fried pork skin; zero-carb crunchy snack"),
            ("WASABI-PEA", "Wasabi Pea", "Pisum sativum", "Pisum", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "Coated crispy peas; wasabi kick; Asian snack"),
        ]
    },
    "CONDIMENTS_SAUCES": {
        "code": "CONDIMENTS_SAUCES", "description": "Condiments, sauces and dressings",
        "items": [
            ("SOY-SAUCE", "Soy Sauce", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Fermented soybean liquid; shoyu and tamari; umami"),
            ("FISH-SAUCE", "Fish Sauce", "Engraulis encrasicolus", "Engraulis", "Chordata", "Actinopterygii", "Clupeiformes", "Engraulidae", "2-3 years", "Fermented anchovy liquid; Thai and Vietnamese staple"),
            ("OYSTER-SAUCE", "Oyster Sauce", "Magallana gigas", "Magallana", "Mollusca", "Bivalvia", "Ostreida", "Ostreidae", "18-36 months", "Thickened oyster extract; stir-fry glaze"),
            ("KETCHUP", "Ketchup (Tomato)", "Solanum lycopersicum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Tomato condiment; sweet and sour; fries staple"),
            ("MUSTARD", "Mustard", "Brassica juncea", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "3-4 months", "Seed paste; Dijon, yellow and whole-grain varieties"),
            ("MAYONNAISE", "Mayonnaise", "Helianthus annuus", "Helianthus", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Egg-oil emulsion; sandwich spread; salad dressing"),
            ("HOT-SAUCE", "Hot Sauce", "Capsicum frutescens", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Chili-vinegar sauce; Tabasco and cayenne blends"),
            ("SRIRACHA", "Sriracha", "Capsicum annuum", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Thai chili-garlic paste; sweet-hot; rooster sauce"),
            ("BALSAMIC-VINEGAR", "Balsamic Vinegar", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Aged grape must vinegar; Modena; syrupy sweet"),
            ("CIDER-VINEGAR", "Apple Cider Vinegar", "Malus domestica", "Malus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Fermented apple vinegar; raw with mother; wellness"),
            ("WORCESTERSHIRE", "Worcestershire Sauce", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Fermented barley vinegar sauce; anchovy-tamarind; steak"),
            ("PESTO", "Pesto Genovese", "Ocimum basilicum", "Ocimum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "2-3 months", "Basil-pine nut-garlic sauce; pasta; Liguria"),
            ("HARISSA", "Harissa", "Capsicum frutescens", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "North African chili paste; roasted peppers; couscous"),
            ("SALSA", "Salsa", "Solanum lycopersicum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Fresh tomato-onion-chili; Mexican condiment"),
            ("TAHINI", "Tahini", "Sesamum indicum", "Sesamum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Pedaliaceae", "3-4 months", "Sesame seed paste; hummus, halva and dressing"),
        ]
    },
    "SWEETENERS": {
        "code": "SWEETENERS", "description": "Natural and traditional sweeteners",
        "items": [
            ("JAGGERY", "Jaggery (Gur)", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Unrefined cane sugar; Indian; retains minerals"),
            ("PALM-SUGAR", "Palm Sugar", "Borassus flabellifer", "Borassus", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "24-36 months", "Coconut or palm sap sugar; Southeast Asian; caramel notes"),
            ("COCONUT-SUGAR", "Coconut Sugar", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Sap-derived granulated sweetener; lower glycemic index"),
            ("DATE-SUGAR", "Date Sugar", "Phoenix dactylifera", "Phoenix", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "5-7 months", "Dehydrated ground dates; fiber-rich; baking"),
            ("BROWN-SUGAR", "Brown Sugar", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Refined sugar with molasses; soft; baking staple"),
            ("MUSCOVADO", "Muscovado", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Unrefined cane sugar; molasses-rich; moist crystals"),
            ("MAPLE-SUGAR", "Maple Sugar", "Acer saccharum", "Acer", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Sapindaceae", "12-18 months", "Dehydrated maple syrup; granulated; Vermont"),
            ("BARLEY-MALT-SYRUP", "Barley Malt Syrup", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Sprouted barley extract; malted baking sweetener"),
            ("RICE-MALT-SYRUP", "Rice Malt Syrup", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Enzymatic rice sweetener; mild; vegan"),
            ("STEVIA", "Stevia Leaf", "Stevia rebaudiana", "Stevia", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Zero-calorie leaf sweetener; rebaudioside extract"),
            ("DATE-SYRUP", "Date Syrup (Silan)", "Phoenix dactylifera", "Phoenix", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "5-7 months", "Reduced date juice; dark and molasses-like; Israeli"),
            ("POMEGRANATE-MOLASSES", "Pomegranate Molasses", "Punica granatum", "Punica", "Magnoliophyta", "Magnoliopsida", "Myrtales", "Lythraceae", "5-6 months", "Reduced pomegranate juice; tart-sweet; Middle Eastern"),
            ("SORGHUM-SYRUP", "Sorghum Syrup", "Sorghum bicolor", "Sorghum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Sweet sorghum juice syrup; American South; pancakes"),
        ]
    },
    "ALCOHOLIC_BEVERAGES": {
        "code": "ALCOHOLIC_BEVERAGES", "description": "Fermented and distilled alcoholic beverages",
        "items": [
            ("WINE-RED", "Red Wine", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Fermented red grapes; tannins; Cabernet and Merlot"),
            ("WINE-WHITE", "White Wine", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Fermented white grapes; Chardonnay and Sauvignon Blanc"),
            ("CHAMPAGNE", "Champagne", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Méthode champenoise sparkling wine; Chardonnay and Pinot"),
            ("BEER-LAGER", "Lager Beer", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Bottom-fermented beer; crisp; pilsner"),
            ("BEER-ALE", "Ale Beer", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Top-fermented beer; fruity; pale ale and IPA"),
            ("STOUT", "Stout", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Dark roasted malt beer; coffee notes; Irish stout"),
            ("SAKE", "Sake (Nihonshu)", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Japanese rice wine; polished rice; served warm or chilled"),
            ("CIDER-HARD", "Hard Cider", "Malus domestica", "Malus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Fermented apple juice; dry to sweet; sparkling"),
            ("WHISKY", "Whisky", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Malted barley spirit; oak-aged; Scotch and bourbon"),
            ("VODKA", "Vodka", "Solanum tuberosum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Neutral grain or potato spirit; clear; martini base"),
            ("RUM", "Rum", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Cane or molasses spirit; aged; Caribbean"),
            ("GIN", "Gin", "Juniperus communis", "Juniperus", "Pinophyta", "Pinopsida", "Pinales", "Cupressaceae", "24-36 months", "Juniper-flavored spirit; London dry; botanicals"),
            ("TEQUILA", "Tequila", "Agave tequilana", "Agave", "Magnoliophyta", "Liliopsida", "Asparagales", "Asparagaceae", "48-60 months", "Blue agave spirit; blanco, reposado and añejo; Mexico"),
            ("BRANDY", "Brandy", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Distilled wine; Cognac and Armagnac; aged in oak"),
        ]
    },
    "ROOT_TUBERS": {
        "code": "ROOT_TUBERS", "description": "Tropical root crops and tubers",
        "items": [
            ("CASSAVA", "Cassava (Manioc)", "Manihot esculenta", "Manihot", "Magnoliophyta", "Magnoliopsida", "Malpighiales", "Euphorbiaceae", "8-12 months", "Starchy root; tapioca, gari and fufu; Africa staple"),
            ("YAM", "Yam", "Dioscorea alata", "Dioscorea", "Magnoliophyta", "Liliopsida", "Dioscoreales", "Dioscoreaceae", "7-9 months", "Large tuber; pounded yam; West Africa"),
            ("TARO", "Taro", "Colocasia esculenta", "Colocasia", "Magnoliophyta", "Liliopsida", "Alismatales", "Araceae", "6-8 months", "Starchy corm; poi and taro chips; Pacific staple"),
            ("COCOYAM", "Cocoyam (Tannia)", "Xanthosoma sagittifolium", "Xanthosoma", "Magnoliophyta", "Liliopsida", "Alismatales", "Araceae", "6-8 months", "Arrow-leaf corm; Caribbean and West African staple"),
            ("ARROWROOT", "Arrowroot", "Maranta arundinacea", "Maranta", "Magnoliophyta", "Liliopsida", "Zingiberales", "Marantaceae", "8-10 months", "Starch rhizome; gluten-free thickener; biscuits"),
            ("LOTUS-ROOT", "Lotus Root", "Nelumbo nucifera", "Nelumbo", "Magnoliophyta", "Magnoliopsida", "Proteales", "Nelumbonaceae", "6-8 months", "Crisp aquatic rhizome; Asian stir-fry and soups"),
            ("SAGO", "Sago", "Metroxylon sagu", "Metroxylon", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "8-12 years", "Palm starch pearls; puddings and bubble tea"),
            ("CANNA-STARCH", "Canna Starch (Queensland Arrowroot)", "Canna indica", "Canna", "Magnoliophyta", "Liliopsida", "Zingiberales", "Cannaceae", "6-8 months", "Edible rhizome starch; Asian noodles and sweets"),
            ("MACA", "Maca Root", "Lepidium meyenii", "Lepidium", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "8-9 months", "Peruvian highland root; superfood powder"),
            ("OCA", "Oca (New Zealand Yam)", "Oxalis tuberosa", "Oxalis", "Magnoliophyta", "Magnoliopsida", "Oxalidales", "Oxalidaceae", "5-6 months", "Colorful Andean tuber; sweet-sour; boiled or roasted"),
            ("MASHUA", "Mashua", "Tropaeolum tuberosum", "Tropaeolum", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Tropaeolaceae", "6-7 months", "Andean tuber; peppery; frost-hardy"),
            ("ULLUCO", "Ulluco", "Ullucus tuberosus", "Ullucus", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Basellaceae", "6-7 months", "Waxy Andean tuber; colorful; soups and salads"),
        ]
    },
    "CITRUS_FRUITS": {
        "code": "CITRUS_FRUITS", "description": "Citrus fruits and varieties",
        "items": [
            ("MANDARIN", "Mandarin Orange", "Citrus reticulata", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "6-8 months", "Easily peeled citrus; seedless; snack fruit"),
            ("CLEMENTINE", "Clementine", "Citrus × clementina", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "6-8 months", "Seedless mandarin hybrid; kid-friendly"),
            ("TANGERINE", "Tangerine", "Citrus reticulata", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "6-8 months", "Deep orange mandarin; fresh and juice"),
            ("GRAPEFRUIT", "Grapefruit", "Citrus × paradisi", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "9-12 months", "Large bitter-sweet citrus; pink or white; breakfast"),
            ("POMELO", "Pomelo", "Citrus maxima", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "10-12 months", "Largest citrus; thick rind; mild sweet flesh"),
            ("CITRON", "Citron", "Citrus medica", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "8-10 months", "Ancient thick-rind citrus; candied peel and etrog"),
            ("KUMQUAT", "Kumquat", "Fortunella japonica", "Fortunella", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "5-6 months", "Eaten whole with peel; tiny fruit; marmalade"),
            ("YUZU", "Yuzu", "Citrus junos", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "8-10 months", "Japanese aromatic citrus; zest and ponzu"),
            ("BLOOD-ORANGE", "Blood Orange", "Citrus × sinensis", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "7-9 months", "Red-fleshed orange; anthocyanins; juice and segments"),
            ("BERGAMOT", "Bergamot", "Citrus × bergamia", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "8-10 months", "Perfumed citrus; Earl Grey tea; zest oil"),
            ("SWEET-LIME", "Sweet Lime (Mosambi)", "Citrus × limetta", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "5-6 months", "Mild non-acidic lime; Indian juice fruit"),
            ("UGLI-FRUIT", "Ugli Fruit (Jamaican Tangelo)", "Citrus reticulata × paradisi", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "8-10 months", "Tangy hybrid; wrinkled skin; easy to peel"),
        ]
    },
    "FERMENTED_PRODUCTS": {
        "code": "FERMENTED_PRODUCTS", "description": "Fermented foods and probiotic products",
        "items": [
            ("SAUERKRAUT", "Sauerkraut", "Brassica oleracea var. capitata", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "3-4 months", "Lacto-fermented cabbage; gut probiotic; German"),
            ("KIMCHI", "Kimchi", "Brassica rapa subsp. pekinensis", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "2-3 months", "Korean fermented napa cabbage; chili and garlic"),
            ("KOMBUCHA", "Kombucha", "Camellia sinensis", "Camellia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Theaceae", "24-36 months", "Fermented sweet tea; SCOBY; fizzy probiotic"),
            ("KEFIR", "Kefir", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "12-24 months", "Fermented milk drink; kefir grains; tangy"),
            ("NATTO", "Natto", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Fermented soybeans; sticky and pungent; Japanese breakfast"),
            ("KVASS", "Kvass", "Secale cereale", "Secale", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Fermented rye bread drink; Slavic; low alcohol"),
            ("KOJI", "Koji Starter", "Aspergillus oryzae", "Aspergillus", "Ascomycota", "Eurotiomycetes", "Eurotiales", "Trichocomaceae", "1-2 weeks", "Malted rice fungus; miso, sake and shoyu base"),
            ("SOUR-PICKLE", "Sour Pickles (Dill)", "Cucumis sativus", "Cucumis", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Lacto-fermented cucumbers; deli classic"),
            ("GOCHUJANG", "Gochujang", "Capsicum annuum", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Korean fermented chili paste; sweet-spicy; bibimbap"),
            ("DOUBANJIANG", "Doubanjiang (Toban Djan)", "Vicia faba", "Vicia", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Fermented fava bean chili paste; Sichuan cooking"),
            ("IDLI-BATTER", "Idli/Dosa Batter", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Fermented rice-lentil batter; South Indian breakfast"),
            ("SOURDOUGH-STARTER", "Sourdough Starter", "Saccharomyces cerevisiae", "Saccharomyces", "Ascomycota", "Saccharomycetes", "Saccharomycetales", "Saccharomycetaceae", "1-2 weeks", "Wild yeast culture; bread leavening; perpetual"),
        ]
    },
    "CUCURBITS_AND_MELONS": {
        "code": "CUCURBITS_AND_MELONS", "description": "Squash, gourds and melons",
        "items": [
            ("PUMPKIN", "Pumpkin", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Orange winter squash; pie, soup and jack-o-lantern"),
            ("BUTTERNUT-SQUASH", "Butternut Squash", "Cucurbita moschata", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Tan bottle squash; sweet nutty; roasting"),
            ("ACORN-SQUASH", "Acorn Squash", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Ridged dark squash; halved baked; maple glaze"),
            ("SPAGHETTI-SQUASH", "Spaghetti Squash", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Stringy flesh when cooked; low-carb pasta"),
            ("KABOCHA-SQUASH", "Kabocha Squash", "Cucurbita maxima", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Japanese pumpkin; dense and sweet; curry"),
            ("DELICATA-SQUASH", "Delicata Squash", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Cream-striped squash; edible skin; roasted"),
            ("BITTER-MELON", "Bitter Melon", "Momordica charantia", "Momordica", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Warty gourd; bitter; Asian stir-fry and juice"),
            ("BOTTLE-GOURD", "Bottle Gourd (Lauki)", "Lagenaria siceraria", "Lagenaria", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Calabash gourd; mild; Indian curry and dosa"),
            ("RIDGE-GOURD", "Ridge Gourd (Turai)", "Luffa acutangula", "Luffa", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Ridged edible gourd; stir-fry; young fruit"),
            ("WINTER-MELON", "Winter Melon (Ash Gourd)", "Benincasa hispida", "Benincasa", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Large wax-coated gourd; soup and candy"),
            ("CHAYOTE", "Chayote", "Sechium edule", "Sechium", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Green pear gourd; crisp; salad and gratin"),
            ("CANTALOUPE", "Cantaloupe (Muskmelon)", "Cucumis melo", "Cucumis", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Netted melon; orange flesh; sweet breakfast fruit"),
            ("HONEYDEW-MELON", "Honeydew Melon", "Cucumis melo", "Cucumis", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Smooth green melon; pale green flesh; juicy"),
        ]
    },
    "HERBAL_MEDICINALS": {
        "code": "HERBAL_MEDICINALS", "description": "Herbal teas and medicinal plants",
        "items": [
            ("CHAMOMILE", "Chamomile", "Matricaria chamomilla", "Matricaria", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "2-3 months", "Calming flower tea; dried heads; sleep aid"),
            ("HIBISCUS", "Hibiscus (Roselle)", "Hibiscus sabdariffa", "Hibiscus", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "3-4 months", "Ruby-red calyx tea; tangy; sour-sweet cooler"),
            ("LAVENDER", "Lavender", "Lavandula angustifolia", "Lavandula", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "3-4 months", "Floral herb; culinary grade; desserts and tea"),
            ("ROSEHIP", "Rosehip", "Rosa canina", "Rosa", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Vitamin C-rich fruit; infusion; jams"),
            ("ELDERFLOWER", "Elderflower", "Sambucus nigra", "Sambucus", "Magnoliophyta", "Magnoliopsida", "Dipsacales", "Adoxaceae", "3-4 months", "Fragrant blossom; cordial and tea; spring"),
            ("GINSENG", "Ginseng", "Panax ginseng", "Panax", "Magnoliophyta", "Magnoliopsida", "Apiales", "Araliaceae", "36-60 months", "Adaptogen root; energy tea; Korea"),
            ("ASHWAGANDHA", "Ashwagandha", "Withania somnifera", "Withania", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "6-8 months", "Indian adaptogen root; stress; ayurvedic"),
            ("MORINGA", "Moringa", "Moringa oleifera", "Moringa", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Moringaceae", "6-8 months", "Nutrient-dense leaf powder; superfood; tea"),
            ("ALOE-VERA", "Aloe Vera", "Aloe barbadensis", "Aloe", "Magnoliophyta", "Liliopsida", "Asparagales", "Asphodelaceae", "18-24 months", "Gel leaf; beverage and digestive; skincare"),
            ("ECHINACEA", "Echinacea", "Echinacea purpurea", "Echinacea", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "2-3 months", "Purple coneflower; immune tea; tincture"),
            ("DANDELION-ROOT", "Dandelion Root", "Taraxacum officinale", "Taraxacum", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Roasted root coffee substitute; liver tonic"),
            ("CALENDULA", "Calendula (Marigold)", "Calendula officinalis", "Calendula", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "2-3 months", "Edible flower; tea and salve; golden petals"),
        ]
    },
}

# ─── LOCAL NAMES (additional language names) ────────────────────
LOCAL_NAMES_INDUSTRY = {
    "ORANGE-JUICE": [("ar", "عصير برتقال"), ("fr", "Jus d'orange"), ("es", "Zumo de naranja"), ("hi", "संतरे का रस")],
    "ICED-TEA": [("ar", "شاي مثلج"), ("zh", "冰茶"), ("fr", "Thé glacé")],
    "OAT-MILK": [("ar", "حليب الشوفان"), ("fr", "Lait d'avoine"), ("es", "Leche de avena")],
    "SOY-MILK": [("zh", "豆奶"), ("ja", "豆乳"), ("ar", "حليب الصويا"), ("fr", "Lait de soja")],
    "CHOCOLATE-DARK": [("ar", "شوكولاتة داكنة"), ("fr", "Chocolat noir"), ("es", "Chocolate negro")],
    "SOURDOUGH-BREAD": [("fr", "Pain au levain"), ("it", "Pane a lievito naturale"), ("de", "Sauerteigbrot")],
    "CROISSANT": [("fr", "Croissant"), ("ar", "كرواسون"), ("it", "Croissant")],
    "POTATO-CHIP": [("ar", "رقائق البطاطس"), ("fr", "Chips de pommes de terre"), ("es", "Patatas fritas")],
    "SOY-SAUCE": [("zh", "酱油"), ("ja", "醤油"), ("ko", "간장"), ("ar", "صلصة الصويا")],
    "FISH-SAUCE": [("th", "น้ำปลา"), ("vi", "Nước mắm"), ("ar", "صلصة السمك")],
    "BALSAMIC-VINEGAR": [("it", "Aceto balsamico"), ("ar", "خل بلسمي"), ("fr", "Vinaigre balsamique")],
    "JAGGERY": [("hi", "गुड़"), ("ur", "گڑ"), ("ar", "سكر جاغري")],
    "WINE-RED": [("ar", "نبيذ أحمر"), ("fr", "Vin rouge"), ("it", "Vino rosso"), ("es", "Vino tinto")],
    "SAKE": [("ja", "日本酒"), ("zh", "清酒"), ("ar", "ساكي")],
    "KIMCHI": [("ko", "김치"), ("ar", "كيمتشي"), ("zh", "泡菜")],
    "KOMBUCHA": [("zh", "康普茶"), ("ja", "コンブチャ"), ("ar", "كومبوتشا")],
    "PUMPKIN": [("ar", "قرع"), ("hi", "कद्दू"), ("fr", "Citrouille"), ("es", "Calabaza")],
    "CHAMOMILE": [("ar", "بابونج"), ("fr", "Camomille"), ("hi", "बबूने के फूल")],
    "HIBISCUS": [("ar", "كركديه"), ("fr", "Hibiscus"), ("es", "Flor de Jamaica")],
    "GINSENG": [("zh", "人参"), ("ko", "인삼"), ("ja", "人参"), ("ar", "جينسينج")],
}

# ─── NUTRITION ATTRIBUTES ────────────────────────────────────────
NUTRITION_INDUSTRY = {
    "ORANGE-JUICE": [("Calories per 100g", "45", "kcal"), ("Vitamin C", "50", "mg"), ("Sugar", "8.4", "g"), ("Potassium", "200", "mg")],
    "OAT-MILK": [("Calories per 100g", "47", "kcal"), ("Carbohydrates", "7", "g"), ("Protein", "1.4", "g"), ("Calcium", "120", "mg")],
    "SOY-MILK": [("Calories per 100g", "54", "kcal"), ("Protein", "3.3", "g"), ("Fat", "1.8", "g"), ("Calcium", "25", "mg")],
    "CHOCOLATE-DARK": [("Calories per 100g", "546", "kcal"), ("Fat", "31", "g"), ("Fiber", "11", "g"), ("Magnesium", "228", "mg")],
    "CHAMOMILE": [("Calories per cup", "2", "kcal"), ("Calcium", "5", "mg"), ("Magnesium", "2", "mg"), ("Flavonoids", "Apigenin", "mg")],
    "PUMPKIN": [("Calories per 100g", "26", "kcal"), ("Vitamin A", "8513", "µg"), ("Fiber", "0.5", "g"), ("Potassium", "340", "mg")],
    "POTATO-CHIP": [("Calories per 100g", "536", "kcal"), ("Fat", "35", "g"), ("Carbohydrates", "53", "g"), ("Sodium", "525", "mg")],
    "KIMCHI": [("Calories per 100g", "24", "kcal"), ("Fiber", "1.6", "g"), ("Vitamin C", "8", "mg"), ("Sodium", "670", "mg")],
    "WINE-RED": [("Calories per 100ml", "85", "kcal"), ("Alcohol", "12.5", "%"), ("Resveratrol", "1.9", "mg")],
    "SAKE": [("Calories per 100ml", "134", "kcal"), ("Alcohol", "15", "%"), ("Carbohydrates", "5", "g")],
    "ALMOND-MILK": [("Calories per 100g", "15", "kcal"), ("Fat", "1.1", "g"), ("Calcium", "188", "mg"), ("Vitamin E", "6.3", "mg")],
    "POPCORN": [("Calories per 100g", "387", "kcal"), ("Fiber", "14.5", "g"), ("Carbohydrates", "78", "g"), ("Protein", "12.9", "g")],
}

# ─── SEED EXECUTION ──────────────────────────────────────────────

async def seed_industry():
    log.info("=" * 56)
    log.info("  FoodTrack Food Industry Category Seed (13 new categories)")
    log.info("=" * 56)

    # Ensure all tables exist with latest schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        existing_codes = set()
        result = await db.execute(select(TaxonomyItem.code))
        for row in result.scalars():
            existing_codes.add(row)

        result = await db.execute(select(Taxonomy).where(Taxonomy.name == "Food Kingdom"))
        tax = result.scalar_one_or_none()
        if not tax:
            log.error("Food Kingdom taxonomy not found. Run seed_food_items.py first.")
            return

        existing_nodes = {}
        result = await db.execute(select(TaxonomyNode).where(TaxonomyNode.taxonomy_id == tax.id))
        for node in result.scalars():
            existing_nodes[node.code] = node

        total_new = 0
        cat_index = len(existing_nodes)

        for cat_name, cat_data in INDUSTRY_CATEGORIES.items():
            node = existing_nodes.get(cat_data["code"])
            if not node:
                cat_index += 1
                node = TaxonomyNode(
                    taxonomy_id=tax.id,
                    parent_id=None,
                    code=cat_data["code"],
                    name=cat_name.replace("_", " ").title(),
                    description=cat_data["description"],
                    sort_order=cat_index * 10,
                    is_active=True,
                )
                db.add(node)
                await db.flush()
                log.info(f"Created new node: {cat_name}")

            for item in cat_data["items"]:
                code = item[0]
                if code in existing_codes:
                    log.debug(f"  Skipping existing: {code}")
                    continue

                (code, common_name, scientific_name, genre, phylum, tax_class, order_name, family, gestation, local_uses) = item[:10]
                gestation_parts = gestation.split("-") if gestation else []
                gestation_period = gestation_parts[0] if gestation_parts and len(gestation_parts) == 1 else (gestation_parts[0] + "-" + gestation_parts[1] if len(gestation_parts) >= 2 else "")
                gestation_unit = "months" if gestation_period else ""

                tax_item = TaxonomyItem(
                    node_id=node.id,
                    code=code,
                    common_name=common_name,
                    scientific_name=scientific_name,
                    genre=genre,
                    phylum=phylum,
                    tax_class=tax_class,
                    order_name=order_name,
                    family=family,
                    gestation_period=gestation_period,
                    gestation_unit=gestation_unit,
                    local_uses=local_uses,
                    description=f"{scientific_name} — {common_name}. {local_uses}. Classification: {phylum} > {tax_class} > {order_name} > {family}.",
                    is_active=True,
                )
                db.add(tax_item)
                await db.flush()

                db.add(ItemName(item_id=tax_item.id, language="en", name=common_name, is_primary=True))
                db.add(ItemName(item_id=tax_item.id, language="scientific", name=scientific_name, is_primary=False))

                if code in LOCAL_NAMES_INDUSTRY:
                    for lang, lname in LOCAL_NAMES_INDUSTRY[code]:
                        db.add(ItemName(item_id=tax_item.id, language=lang, name=lname, is_primary=False))

                if code in NUTRITION_INDUSTRY:
                    for key, value, unit in NUTRITION_INDUSTRY[code]:
                        db.add(ItemAttribute(item_id=tax_item.id, key=key, value=str(value), unit=unit))

                total_new += 1
                if total_new % 20 == 0:
                    log.info(f"  ... {total_new} new items seeded so far")

        await db.commit()
        log.info(f"Seeded {total_new} NEW taxonomy items across {len(INDUSTRY_CATEGORIES)} categories")
        total_result = await db.execute(select(func.count(TaxonomyItem.id)))
        log.info(f"Total taxonomy items now: {total_result.scalar()}")
        log.info("Done!")


if __name__ == "__main__":
    asyncio.run(seed_industry())
