"""
FoodTrack -- Comprehensive Food Taxonomy Seed
Seeds the database with 120+ food items organised by category,
each with full taxonomic metadata (phylum, family, genus, class, order, local names, uses).
"""
import asyncio, sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from sqlalchemy import select, func

from app.database import async_session, engine, Base
from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute
from app.models.product import Product, ProductCategory
from app.models.user import User
from app.models.tracking import (
    Warehouse, Batch, BatchStatus, Shipment, ShipmentStatus, ShipmentMode,
    ShipmentBatch, TrackingEvent, ShipmentTrackingEvent,
)
from app.models.certificate import Certificate, CertificateStatus, CertificateType
from app.models.traceability import TraceabilityEvent, EventType

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

# ─── TAXONOMY STRUCTURE ──────────────────────────────────────────
# We create one master taxonomy: "Food Kingdom" with nodes per category

FOOD_CATEGORIES = {
    "GRAINS": {
        "code": "GRAINS", "description": "Edible grains and cereals",
        "items": [
            ("MAIZE-WHITE", "White Maize", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Staple food in Africa; maize flour, porridge, animal feed"),
            ("MAIZE-YELLOW", "Yellow Maize", "Zea mays var. indentata", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Animal feed, sweet corn, ethanol production"),
            ("RICE-LONG", "Long Grain Rice", "Oryza sativa indica", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Basmati, Jasmine; South Asian staple"),
            ("RICE-SHORT", "Short Grain Rice", "Oryza sativa japonica", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Sushi rice; East Asian staple"),
            ("RICE-AROMATIC", "Aromatic Rice (Basmati)", "Oryza sativa basmati", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "5-7 months", "Premium long-grain; grown in India/Pakistan"),
            ("RICE-GLUTINOUS", "Glutinous Rice", "Oryza sativa glutinosa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Sticky rice; used in desserts and dumplings"),
            ("WHEAT-HARD", "Hard Red Wheat", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Bread flour; high protein"),
            ("WHEAT-SOFT", "Soft White Wheat", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Pastry flour; low protein"),
            ("WHEAT-DURUM", "Durum Wheat", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "7-9 months", "Pasta, semolina production"),
            ("SORGHUM", "Sorghum", "Sorghum bicolor", "Sorghum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Drought-tolerant grain; gluten-free flour"),
            ("MILLET", "Pearl Millet", "Pennisetum glaucum", "Pennisetum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "3-4 months", "Dryland staple; rich in iron"),
            ("BARLEY", "Barley", "Hordeum vulgare", "Hordeum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Beer malting; animal feed; soup grain"),
            ("OATS", "Oats", "Avena sativa", "Avena", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "5-7 months", "Porridge, oat milk, rolled oats"),
            ("RYE", "Rye", "Secale cereale", "Secale", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Rye bread, whisky, animal feed"),
            ("QUINOA", "Quinoa", "Chenopodium quinoa", "Chenopodium", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "4-6 months", "High-protein pseudocereal; gluten-free"),
        ]
    },
    "LEGUMES": {
        "code": "LEGUMES", "description": "Edible legumes, beans and pulses",
        "items": [
            ("RICE-BEAN", "Rice Bean", "Vigna umbellata", "Vigna", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Small reddish bean; grown in Asia"),
            ("MUNG-BEAN", "Mung Bean", "Vigna radiata", "Vigna", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "Bean sprouts; dal; green gram"),
            ("BLACK-GRAM", "Black Gram (Urad)", "Vigna mungo", "Vigna", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Used in dosa, idli; rich in protein"),
            ("RED-LENTIL", "Red Lentil", "Lens culinaris", "Lens", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Quick-cooking lentil; soup staple"),
            ("GREEN-LENTIL", "Green Lentil", "Lens culinaris", "Lens", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Whole lentil; holds shape when cooked"),
            ("CHICKPEA-DESi", "Desi Chickpea", "Cicer arietinum", "Cicer", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Small dark chickpea; Indian subcontinent"),
            ("CHICKPEA-KABULI", "Kabuli Chickpea", "Cicer arietinum", "Cicer", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Large cream chickpea; hummus"),
            ("SOYBEAN", "Soybean", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Tofu, soy milk, oil, animal feed"),
            ("GROUNDNUT", "Groundnut (Peanut)", "Arachis hypogaea", "Arachis", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Oil, roasted snack, peanut butter"),
            ("PIGEON-PEA", "Pigeon Pea (Toor)", "Cajanus cajan", "Cajanus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "5-6 months", "Split pea used in dal; drought hardy"),
            ("COWPEA", "Cowpea", "Vigna unguiculata", "Vigna", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Black-eyed pea; leafy green and grain"),
            ("FABA-BEAN", "Fava Bean", "Vicia faba", "Vicia", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "Broad bean; Mediterranean staple"),
            ("KIDNEY-BEAN", "Kidney Bean", "Phaseolus vulgaris", "Phaseolus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Red kidney bean; chili, rice dishes"),
        ]
    },
    "TROPICAL_FRUITS": {
        "code": "TROPICAL_FRUITS", "description": "Tropical and subtropical fruits",
        "items": [
            ("MANGO-ALPHONSO", "Alphonso Mango", "Mangifera indica", "Mangifera", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "4-5 months", "Premium Indian mango; sweet, creamy"),
            ("MANGO-KEITT", "Keitt Mango", "Mangifera indica", "Mangifera", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "5-6 months", "Late-season variety; Kenya/Egypt export"),
            ("BANANA-CAVENDISH", "Cavendish Banana", "Musa acuminata", "Musa", "Magnoliophyta", "Liliopsida", "Zingiberales", "Musaceae", "9-12 months", "Export banana; dessert type"),
            ("BANANA-PLANTAIN", "Plantain", "Musa × paradisiaca", "Musa", "Magnoliophyta", "Liliopsida", "Zingiberales", "Musaceae", "10-12 months", "Cooking banana; staple in W. Africa"),
            ("PINEAPPLE", "Pineapple", "Ananas comosus", "Ananas", "Magnoliophyta", "Liliopsida", "Poales", "Bromeliaceae", "18-24 months", "Sweet tropical fruit; canned, fresh"),
            ("PAPAYA", "Papaya", "Carica papaya", "Carica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Caricaceae", "6-9 months", "Orange-fleshed fruit; rich in papain"),
            ("AVOCADO-HASS", "Hass Avocado", "Persea americana", "Persea", "Magnoliophyta", "Magnoliopsida", "Laurales", "Lauraceae", "5-7 months", "Dark-skinned avocado; creamy texture"),
            ("AVOCADO-FUERTE", "Fuerte Avocado", "Persea americana", "Persea", "Magnoliophyta", "Magnoliopsida", "Laurales", "Lauraceae", "4-6 months", "Green-skinned; smooth, mild flavor"),
            ("COCONUT", "Coconut", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Water, milk, oil, meat from drupe"),
            ("PASSION-FRUIT", "Passion Fruit", "Passiflora edulis", "Passiflora", "Magnoliophyta", "Magnoliopsida", "Malpighiales", "Passifloraceae", "3-4 months", "Purple or yellow; aromatic juice"),
            ("GUAVA", "Guava", "Psidium guajava", "Psidium", "Magnoliophyta", "Magnoliopsida", "Myrtales", "Myrtaceae", "4-5 months", "Pink or white flesh; rich in Vitamin C"),
            ("DRAGON-FRUIT", "Dragon Fruit", "Hylocereus undatus", "Hylocereus", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Cactaceae", "4-6 months", "White/red flesh; mild sweet taste"),
            ("LYCHEE", "Lychee", "Litchi chinensis", "Litchi", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Sapindaceae", "3-4 months", "Translucent sweet flesh; Asian delicacy"),
            ("DURIAN", "Durian", "Durio zibethinus", "Durio", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "4-5 months", "King of fruits; strong aroma; custard-like"),
        ]
    },
    "TEMPERATE_FRUITS": {
        "code": "TEMPERATE_FRUITS", "description": "Temperate and Mediterranean fruits",
        "items": [
            ("APPLE-FUJI", "Fuji Apple", "Malus domestica", "Malus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Sweet, crisp; Japan origin; long storage"),
            ("APPLE-GRANNY", "Granny Smith Apple", "Malus domestica", "Malus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Green, tart; excellent for baking"),
            ("GRAPE-RED", "Red Globe Grape", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Large red table grape; seeds"),
            ("GRAPE-GREEN", "Thompson Seedless", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Green seedless; raisins, table"),
            ("ORANGE-NAVEL", "Navel Orange", "Citrus × sinensis", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "6-8 months", "Seedless eating orange; sweet"),
            ("ORANGE-VALENCIA", "Valencia Orange", "Citrus × sinensis", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "7-9 months", "Juice orange; late season"),
            ("LEMON", "Lemon", "Citrus × limon", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "5-6 months", "Yellow citrus; sour juice, zest"),
            ("LIME", "Lime", "Citrus × aurantiifolia", "Citrus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Rutaceae", "4-5 months", "Green citrus; key lime, juice"),
            ("STRAWBERRY", "Strawberry", "Fragaria × ananassa", "Fragaria", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "3-4 months", "Red berry; fresh, frozen, jam"),
            ("BLUEBERRY", "Blueberry", "Vaccinium corymbosum", "Vaccinium", "Magnoliophyta", "Magnoliopsida", "Ericales", "Ericaceae", "3-5 months", "Highbush blueberry; antioxidant-rich"),
            ("PEACH", "Peach", "Prunus persica", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "3-4 months", "Yellow/white flesh; freestone/clingstone"),
            ("PEAR-BOSC", "Bosc Pear", "Pyrus communis", "Pyrus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "4-5 months", "Brown russet; sweet, spicy flavor"),
            ("WATERMELON", "Watermelon", "Citrullus lanatus", "Citrullus", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Large melon; red flesh; summer fruit"),
            ("CHERRY", "Sweet Cherry", "Prunus avium", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "2-3 months", "Bing, Rainier; dessert cherry"),
        ]
    },
    "VEGETABLES": {
        "code": "VEGETABLES", "description": "Leafy greens, root vegetables, and culinary vegetables",
        "items": [
            ("KALE", "Kale", "Brassica oleracea var. sabellica", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "2-3 months", "Curly leaf; superfood; cold hardy"),
            ("SPINACH", "Spinach", "Spinacia oleracea", "Spinacia", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "1-2 months", "Leafy green; rich in iron and vitamins"),
            ("CABBAGE", "Cabbage", "Brassica oleracea var. capitata", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "3-4 months", "Round head; slaw, sauerkraut"),
            ("BROCCOLI", "Broccoli", "Brassica oleracea var. italica", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "3-4 months", "Green florets; rich in sulforaphane"),
            ("CAULIFLOWER", "Cauliflower", "Brassica oleracea var. botrytis", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "3-4 months", "White curd; versatile vegetable"),
            ("CARROT", "Carrot", "Daucus carota subsp. sativus", "Daucus", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Orange root; rich in beta-carotene"),
            ("POTATO", "Potato", "Solanum tuberosum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Tuber staple; chips, mash, boiled"),
            ("SWEET-POTATO", "Sweet Potato", "Ipomoea batatas", "Ipomoea", "Magnoliophyta", "Magnoliopsida", "Solanales", "Convolvulaceae", "4-5 months", "Orange flesh; baked, fries, puree"),
            ("ONION-RED", "Red Onion", "Allium cepa", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "4-5 months", "Purple skin; milder; salad use"),
            ("ONION-WHITE", "White Onion", "Allium cepa", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "4-5 months", "White flesh; cooking staple"),
            ("GARLIC", "Garlic", "Allium sativum", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "6-7 months", "Pungent bulb; seasoning, medicinal"),
            ("TOMATO", "Tomato", "Solanum lycopersicum", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Red fruit used as vegetable; sauce, salad"),
            ("CUCUMBER", "Cucumber", "Cucumis sativus", "Cucumis", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Green cylindrical; salad pickling"),
            ("BELL-PEPPER", "Bell Pepper", "Capsicum annuum", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Red/green/yellow; sweet capsicum"),
            ("CHILLI", "Red Chilli", "Capsicum frutescens", "Capsicum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Hot pepper; dried, fresh, spice"),
        ]
    },
    "HERBS_SPICES": {
        "code": "HERBS_SPICES", "description": "Culinary herbs and spices",
        "items": [
            ("CORIANDER", "Coriander Leaf", "Coriandrum sativum", "Coriandrum", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "1-2 months", "Fresh herb; leaves and seeds used"),
            ("CUMIN", "Cumin", "Cuminum cyminum", "Cuminum", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Earthy spice; curry, cumin seed"),
            ("TURMERIC", "Turmeric", "Curcuma longa", "Curcuma", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "7-9 months", "Yellow rhizome; curcumin; curry color"),
            ("GINGER", "Ginger", "Zingiber officinale", "Zingiber", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "8-10 months", "Pungent rhizome; tea, cooking, medicinal"),
            ("BLACK-PEPPER", "Black Pepper", "Piper nigrum", "Piper", "Magnoliophyta", "Magnoliopsida", "Piperales", "Piperaceae", "4-5 months", "Black/white peppercorns; table spice"),
            ("CINNAMON", "Cinnamon", "Cinnamomum verum", "Cinnamomum", "Magnoliophyta", "Magnoliopsida", "Laurales", "Lauraceae", "24-36 months", "Sri Lankan; bark quills; sweet spice"),
            ("MINT-PEPPERMINT", "Peppermint", "Mentha × piperita", "Mentha", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "2-3 months", "Cooling herb; tea, garnish, oil"),
            ("BASIL", "Sweet Basil", "Ocimum basilicum", "Ocimum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "2-3 months", "Italian herb; pesto, salad, garnish"),
            ("ROSEMARY", "Rosemary", "Salvia rosmarinus", "Salvia", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "6-9 months", "Woody herb; roast meats, bread"),
            ("THYME", "Thyme", "Thymus vulgaris", "Thymus", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "3-4 months", "Small-leaf herb; stews, poultry"),
            ("SAFFRON", "Saffron", "Crocus sativus", "Crocus", "Magnoliophyta", "Liliopsida", "Asparagales", "Iridaceae", "4-5 months", "Dried stigma; costliest spice; golden color"),
            ("NUTMEG", "Nutmeg", "Myristica fragrans", "Myristica", "Magnoliophyta", "Magnoliopsida", "Magnoliales", "Myristicaceae", "7-9 months", "Warm spice; baked goods, eggnog"),
            ("CLOVE", "Clove", "Syzygium aromaticum", "Syzygium", "Magnoliophyta", "Magnoliopsida", "Myrtales", "Myrtaceae", "5-6 months", "Dried flower bud; pungent spice"),
            ("VANILLA", "Vanilla", "Vanilla planifolia", "Vanilla", "Magnoliophyta", "Liliopsida", "Asparagales", "Orchidaceae", "24-36 months", "Orchid pod; ice cream, baking"),
        ]
    },
    "SEAFOOD": {
        "code": "SEAFOOD", "description": "Fish, shellfish and marine food products",
        "items": [
            ("TILAPIA", "Tilapia", "Oreochromis niloticus", "Oreochromis", "Chordata", "Actinopterygii", "Cichliformes", "Cichlidae", "6-8 months", "Freshwater fish; mild white flesh"),
            ("SALMON-ATLANTIC", "Atlantic Salmon", "Salmo salar", "Salmo", "Chordata", "Actinopterygii", "Salmoniformes", "Salmonidae", "24-30 months", "Farmed salmon; rich in Omega-3"),
            ("TUNA-SKIPJACK", "Skipjack Tuna", "Katsuwonus pelamis", "Katsuwonus", "Chordata", "Actinopterygii", "Scombriformes", "Scombridae", "12-18 months", "Canned tuna; tropical waters"),
            ("SHRIMP-WHITE", "Whiteleg Shrimp", "Litopenaeus vannamei", "Litopenaeus", "Arthropoda", "Malacostraca", "Decapoda", "Penaeidae", "4-5 months", "Farmed white shrimp; global trade"),
            ("MACKEREL", "Atlantic Mackerel", "Scomber scombrus", "Scomber", "Chordata", "Actinopterygii", "Scombriformes", "Scombridae", "12-18 months", "Oily fish; smoked, canned, grilled"),
            ("COD-ATLANTIC", "Atlantic Cod", "Gadus morhua", "Gadus", "Chordata", "Actinopterygii", "Gadiformes", "Gadidae", "24-36 months", "White fish; fish and chips, salted"),
            ("SARDINE", "European Sardine", "Sardina pilchardus", "Sardina", "Chordata", "Actinopterygii", "Clupeiformes", "Clupeidae", "3-5 years", "Small oily fish; canned, grilled"),
            ("CRAB-BLUE", "Blue Crab", "Callinectes sapidus", "Callinectes", "Arthropoda", "Malacostraca", "Decapoda", "Portunidae", "12-18 months", "Atlantic blue crab; meat, soft shell"),
        ]
    },
    "DAIRY_EGGS": {
        "code": "DAIRY_EGGS", "description": "Dairy products and eggs",
        "items": [
            ("MILK-COW", "Cow Milk", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "12-24 months", "Whole milk; pasteurised/UHT; dairy staple"),
            ("EGG-CHICKEN", "Chicken Egg", "Gallus gallus domesticus", "Gallus", "Chordata", "Aves", "Galliformes", "Phasianidae", "4-5 months", "Table egg; white/brown; versatile protein"),
            ("CHEESE-CHEDDAR", "Cheddar Cheese", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "2-24 months", "Hard cow milk cheese; aged cheddar"),
            ("YOGURT", "Plain Yogurt", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "1-2 months", "Cultured milk; probiotic; plain/Greek"),
            ("BUTTER", "Butter", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "3-6 months", "Dairy butter; salted/unsalted; cooking fat"),
        ]
    },
}

# ─── LOCAL NAMES (additional language names) ────────────────────
LOCAL_NAMES = {
    "MAIZE-WHITE": [("sw", "Mahindi meupe"), ("lg", "Muwemba"), ("pt", "Milho branco")],
    "MAIZE-YELLOW": [("sw", "Mahindi ya manjano"), ("lg", "Kasooli"), ("pt", "Milho amarelo")],
    "RICE-LONG": [("sw", "Mchele mrefu"), ("ar", "أرز طويل الحبة"), ("hi", "लंबा चावल")],
    "RICE-AROMATIC": [("ur", "باسمتی چاول"), ("hi", "बासमती चावल"), ("ar", "أرز بسمتي")],
    "SORGHUM": [("sw", "Mtama"), ("lg", "Oburo"), ("yo", "Oka baba")],
    "MILLET": [("sw", "Ulezi"), ("lg", "Obulo"), ("hi", "बाजरा")],
    "MUNG-BEAN": [("hi", "मूंग दाल"), ("zh", "绿豆"), ("sw", "Choroko")],
    "CHICKPEA-DESi": [("hi", "काला चना"), ("ur", "کالا چنا"), ("sw", "Mbaazi")],
    "SOYBEAN": [("zh", "大豆"), ("hi", "सोयाबीन"), ("sw", "Soya")],
    "MANGO-ALPHONSO": [("hi", "हापुस आम"), ("mr", "हापुस आंबा"), ("ar", "مانجو ألفونسو")],
    "BANANA-CAVENDISH": [("sw", "Ndizi mbivu"), ("lg", "Matooke"), ("fr", "Banane dessert")],
    "COCONUT": [("sw", "Nazi"), ("tl", "Niyog"), ("hi", "नारियल")],
    "POTATO": [("sw", "Viazi"), ("lg", "Lumonde"), ("hi", "आलू")],
    "SWEET-POTATO": [("sw", "Viazi vitamu"), ("lg", "Lumonde"), ("pt", "Batata-doce")],
    "TOMATO": [("sw", "Nyanya"), ("lg", "Nyaanya"), ("ar", "طماطم")],
    "ONION-RED": [("sw", "Kitunguu nyekundu"), ("lg", "Katungulu"), ("ar", "بصل أحمر")],
    "GARLIC": [("sw", "Kitunguu saumu"), ("ar", "ثوم"), ("hi", "लहसुन")],
    "GINGER": [("sw", "Tangawizi"), ("hi", "अदरक"), ("zh", "姜")],
    "TURMERIC": [("sw", "Manjano"), ("hi", "हल्दी"), ("zh", "姜黄")],
    "BLACK-PEPPER": [("sw", "Pilipili manga"), ("hi", "काली मिर्च"), ("zh", "黑胡椒")],
    "TILAPIA": [("sw", "Sato"), ("lg", "Ngege"), ("fr", "Tilapia du Nil")],
    "SHRIMP-WHITE": [("sw", "Kamba"), ("zh", "南美白虾"), ("fr", "Crevette blanche")],
    "MILK-COW": [("sw", "Maziwa ya ng'ombe"), ("ar", "حليب البقر"), ("hi", "गाय का दूध")],
    "EGG-CHICKEN": [("sw", "Yai la kuku"), ("lg", "Eggi"), ("ar", "بيض الدجاج")],
}

# ─── NUTRITION ATTRIBUTES ────────────────────────────────────────
NUTRITION = {
    "MAIZE-WHITE": [("Calories per 100g", "365", "kcal"), ("Protein", "9.4", "g"), ("Carbohydrates", "74", "g"), ("Fat", "4.7", "g")],
    "RICE-LONG": [("Calories per 100g", "365", "kcal"), ("Protein", "7.1", "g"), ("Carbohydrates", "80", "g"), ("Fat", "0.7", "g")],
    "WHEAT-HARD": [("Calories per 100g", "327", "kcal"), ("Protein", "12.6", "g"), ("Carbohydrates", "71", "g"), ("Fat", "1.5", "g")],
    "CHICKPEA-DESi": [("Calories per 100g", "364", "kcal"), ("Protein", "19", "g"), ("Carbohydrates", "61", "g"), ("Fiber", "17", "g")],
    "MANGO-ALPHONSO": [("Calories per 100g", "60", "kcal"), ("Vitamin C", "36", "mg"), ("Sugar", "14", "g")],
    "AVOCADO-HASS": [("Calories per 100g", "160", "kcal"), ("Fat", "15", "g"), ("Fiber", "7", "g"), ("Potassium", "485", "mg")],
    "BANANA-CAVENDISH": [("Calories per 100g", "89", "kcal"), ("Potassium", "358", "mg"), ("Sugar", "12", "g")],
    "SALMON-ATLANTIC": [("Calories per 100g", "208", "kcal"), ("Protein", "20", "g"), ("Omega-3", "2.2", "g"), ("Fat", "13", "g")],
    "POTATO": [("Calories per 100g", "77", "kcal"), ("Carbohydrates", "17", "g"), ("Vitamin C", "19.7", "mg"), ("Potassium", "421", "mg")],
    "SPINACH": [("Calories per 100g", "23", "kcal"), ("Iron", "2.7", "mg"), ("Vitamin K", "483", "µg"), ("Vitamin A", "469", "µg")],
}

# ─── SEED EXECUTION ──────────────────────────────────────────────

async def seed():
    log.info("=" * 56)
    log.info("  FoodTrack Food Taxonomy Seed")
    log.info("=" * 56)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Check if already seeded
        existing = await db.execute(select(func.count(TaxonomyItem.id)))
        if existing.scalar() > 10:
            log.info(f"Already seeded ({existing.scalar()} taxonomy items). Skipping.")
            return

        # Create "Food Kingdom" taxonomy
        tax = Taxonomy(name="Food Kingdom", description="Comprehensive food and agricultural product taxonomy", icon="🌾", is_active=True)
        db.add(tax)
        await db.flush()
        log.info(f"Created taxonomy: {tax.name} (ID={tax.id})")

        total_items = 0
        cat_index = 0

        for cat_name, cat_data in FOOD_CATEGORIES.items():
            cat_index += 1
            # Create category node
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

            # Create items under this node
            for item in cat_data["items"]:
                code, common_name, scientific_name, genre, phylum, tax_class, order_name, family, gestation, local_uses = item
                gestation_parts = gestation.split("-")
                gestation_period = gestation_parts[0] if len(gestation_parts) == 1 else (gestation_parts[0] + "-" + gestation_parts[1])
                gestation_unit = "months"

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
                await db.flush()  # flush to get id

                # Add primary English name
                db.add(ItemName(item_id=tax_item.id, language="en", name=common_name, is_primary=True))

                # Add scientific name as a name entry
                db.add(ItemName(item_id=tax_item.id, language="scientific", name=scientific_name, is_primary=False))

                # Add local names
                if code in LOCAL_NAMES:
                    for lang, lname in LOCAL_NAMES[code]:
                        db.add(ItemName(item_id=tax_item.id, language=lang, name=lname, is_primary=False))

                # Add nutrition attributes
                if code in NUTRITION:
                    for key, value, unit in NUTRITION[code]:
                        db.add(ItemAttribute(item_id=tax_item.id, key=key, value=str(value), unit=unit))

                total_items += 1

        await db.commit()
        log.info(f"Seeded {total_items} taxonomy items across {len(FOOD_CATEGORIES)} categories ✓")
        log.info("Done!")

if __name__ == "__main__":
    asyncio.run(seed())