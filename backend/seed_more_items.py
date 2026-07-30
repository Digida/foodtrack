"""
FoodTrack -- Additional Food Taxonomy Seed (200+ items)
Adds new categories and items to the existing Food Kingdom taxonomy.
"""
import asyncio, sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timezone
from sqlalchemy import select, func

from app.database import async_session, engine, Base
from app.models.taxonomy import Taxonomy, TaxonomyNode, TaxonomyItem, ItemName, ItemAttribute

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

NEW_CATEGORIES = {
    "NUTS_SEEDS": {
        "code": "NUTS_SEEDS", "description": "Tree nuts and edible seeds",
        "items": [
            ("ALMOND", "Almond", "Prunus dulcis", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "5-6 months", "Tree nut; raw, roasted, almond milk, almond flour; rich in Vitamin E"),
            ("WALNUT", "English Walnut", "Juglans regia", "Juglans", "Magnoliophyta", "Magnoliopsida", "Fagales", "Juglandaceae", "4-5 months", "Omega-3 rich nut; baking, oil, snack"),
            ("CASHEW", "Cashew Nut", "Anacardium occidentale", "Anacardium", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "6-8 months", "Kidney-shaped nut; raw, roasted, cashew butter, dairy alternative"),
            ("PISTACHIO", "Pistachio", "Pistacia vera", "Pistacia", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "5-6 months", "Green edible seed; snack, ice cream, confectionery"),
            ("PECAN", "Pecan", "Carya illinoinensis", "Carya", "Magnoliophyta", "Magnoliopsida", "Fagales", "Juglandaceae", "6-8 months", "North American nut; pecan pie, praline, snack"),
            ("MACADAMIA", "Macadamia Nut", "Macadamia integrifolia", "Macadamia", "Magnoliophyta", "Magnoliopsida", "Proteales", "Proteaceae", "6-8 months", "Australian native; buttery texture, high oil content"),
            ("BRAZIL-NUT", "Brazil Nut", "Bertholletia excelsa", "Bertholletia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Lecythidaceae", "12-14 months", "Amazonian nut; rich in selenium and magnesium"),
            ("HAZELNUT", "Hazelnut (Filbert)", "Corylus avellana", "Corylus", "Magnoliophyta", "Magnoliopsida", "Fagales", "Betulaceae", "4-5 months", "Round nut; Nutella, praline, roasted snack"),
            ("PINE-NUT", "Pine Nut (Pignoli)", "Pinus pinea", "Pinus", "Pinophyta", "Pinopsida", "Pinales", "Pinaceae", "24-36 months", "Edible seed from pine cones; pesto, Mediterranean cuisine"),
            ("CHESTNUT", "Sweet Chestnut", "Castanea sativa", "Castanea", "Magnoliophyta", "Magnoliopsida", "Fagales", "Fagaceae", "4-5 months", "Starchy nut; roasted, flour, stuffing"),
            ("SESAME-SEED", "Sesame Seed", "Sesamum indicum", "Sesamum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Pedaliaceae", "3-4 months", "Oilseed; tahini, sesame oil, bread topping"),
            ("SUNFLOWER-SEED", "Sunflower Seed", "Helianthus annuus", "Helianthus", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Edible seed; snack, oil, bird feed"),
            ("PUMPKIN-SEED", "Pumpkin Seed (Pepita)", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "3-4 months", "Flat green seed; roasted snack, pesto, oil"),
            ("FLAX-SEED", "Flax Seed (Linseed)", "Linum usitatissimum", "Linum", "Magnoliophyta", "Magnoliopsida", "Malpighiales", "Linaceae", "3-4 months", "Omega-3 rich seed; ground meal, oil, baking"),
            ("CHIA-SEED", "Chia Seed", "Salvia hispanica", "Salvia", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "3-4 months", "Gelling seed; pudding, smoothie, gluten-free baking"),
            ("HEMP-SEED", "Hemp Seed", "Cannabis sativa", "Cannabis", "Magnoliophyta", "Magnoliopsida", "Rosales", "Cannabaceae", "3-4 months", "Nutty seed; hemp milk, protein powder, oil"),
            ("POPPY-SEED", "Poppy Seed", "Papaver somniferum", "Papaver", "Magnoliophyta", "Magnoliopsida", "Ranunculales", "Papaveraceae", "3-4 months", "Tiny blue-black seed; baking, bagel topping, filling"),
            ("FENNEL-SEED", "Fennel Seed", "Foeniculum vulgare", "Foeniculum", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Sweet aromatic seed; spice, tea, digestive aid"),
        ]
    },
    "MEAT_POULTRY": {
        "code": "MEAT_POULTRY", "description": "Meat, poultry and game products",
        "items": [
            ("BEEF", "Beef (Cattle)", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "18-24 months", "Red meat; steaks, roasts, mince, offal; global protein staple"),
            ("CHICKEN", "Chicken (Broiler)", "Gallus gallus domesticus", "Gallus", "Chordata", "Aves", "Galliformes", "Phasianidae", "5-7 weeks", "Poultry meat; breast, thigh, wing, drumstick; lean protein"),
            ("PORK", "Pork (Pig)", "Sus scrofa domesticus", "Sus", "Chordata", "Mammalia", "Artiodactyla", "Suidae", "5-7 months", "Porcine meat; bacon, ham, chops, shoulder, ribs"),
            ("LAMB", "Lamb (Sheep)", "Ovis aries", "Ovis", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "6-12 months", "Young sheep meat; chops, leg, shoulder, rack"),
            ("GOAT", "Goat Meat (Chevon)", "Capra hircus", "Capra", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "6-9 months", "Lean red meat; curry, stew; widely consumed in Asia/Africa/Caribbean"),
            ("DUCK", "Duck (Pekin)", "Anas platyrhynchos domesticus", "Anas", "Chordata", "Aves", "Anseriformes", "Anatidae", "6-8 weeks", "Waterfowl meat; roast duck, confit, magret, foie gras"),
            ("TURKEY", "Turkey", "Meleagris gallopavo", "Meleagris", "Chordata", "Aves", "Galliformes", "Phasianidae", "14-20 weeks", "Large poultry; roast, minced, deli meat; Thanksgiving staple"),
            ("RABBIT", "Rabbit Meat", "Oryctolagus cuniculus", "Oryctolagus", "Chordata", "Mammalia", "Lagomorpha", "Leporidae", "3-4 months", "White meat; lean, mild flavor; stew, roast, paella"),
            ("VENISON", "Venison (Deer)", "Cervus elaphus", "Cervus", "Chordata", "Mammalia", "Artiodactyla", "Cervidae", "18-24 months", "Game meat; lean, rich flavor; steak, roast, jerky"),
            ("BUFFALO", "Buffalo Meat (Water Buffalo)", "Bubalus bubalis", "Bubalus", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "24-30 months", "Lean red meat; lower fat than beef; Asian/S. American staple"),
            ("QUAIL", "Quail", "Coturnix japonica", "Coturnix", "Chordata", "Aves", "Galliformes", "Phasianidae", "5-6 weeks", "Small game bird; tender meat; grilled, roasted, eggs also used"),
            ("GOOSE", "Goose", "Anser anser domesticus", "Anser", "Chordata", "Aves", "Anseriformes", "Anatidae", "4-5 months", "Fatty poultry; roast goose, foie gras, rendered fat"),
        ]
    },
    "BEVERAGE_CROPS": {
        "code": "BEVERAGE_CROPS", "description": "Crops processed into beverages",
        "items": [
            ("COFFEE-ARABICA", "Arabica Coffee", "Coffea arabica", "Coffea", "Magnoliophyta", "Magnoliopsida", "Gentianales", "Rubiaceae", "36-48 months", "Premium coffee species; smooth, complex flavor; high-altitude grown"),
            ("COFFEE-ROBUSTA", "Robusta Coffee", "Coffea canephora", "Coffea", "Magnoliophyta", "Magnoliopsida", "Gentianales", "Rubiaceae", "24-36 months", "High-caffeine coffee; bitter, full-bodied; instant coffee"),
            ("TEA-GREEN", "Green Tea", "Camellia sinensis", "Camellia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Theaceae", "24-36 months", "Unoxidized tea leaves; high antioxidants; Sencha, Matcha, Longjing"),
            ("TEA-BLACK", "Black Tea", "Camellia sinensis", "Camellia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Theaceae", "24-36 months", "Fully oxidized tea; Assam, Darjeeling, Earl Grey, English Breakfast"),
            ("COCOA", "Cocoa (Cacao)", "Theobroma cacao", "Theobroma", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "36-48 months", "Chocolate source; cocoa beans, cocoa butter, cocoa powder"),
            ("MATE", "Yerba Mate", "Ilex paraguariensis", "Ilex", "Magnoliophyta", "Magnoliopsida", "Aquifoliales", "Aquifoliaceae", "24-36 months", "Caffeinated herbal tea; South American staple; served in gourd"),
            ("ROOIBOS", "Rooibos (Red Bush)", "Aspalathus linearis", "Aspalathus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "18-24 months", "South African herbal tea; caffeine-free; rich in antioxidants"),
            ("HOPS", "Hops", "Humulus lupulus", "Humulus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Cannabaceae", "4-5 months", "Beer bittering agent; preserved beer, adds aroma; cone flower"),
        ]
    },
    "OILS_FATS": {
        "code": "OILS_FATS", "description": "Edible oils and fats",
        "items": [
            ("OLIVE-OIL", "Olive Oil", "Olea europaea", "Olea", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Oleaceae", "5-7 months", "Mediterranean oil; extra virgin, virgin, refined; monounsaturated fat"),
            ("PALM-OIL", "Palm Oil", "Elaeis guineensis", "Elaeis", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "24-30 months", "Most widely used vegetable oil; semi-solid at room temperature"),
            ("SUNFLOWER-OIL", "Sunflower Oil", "Helianthus annuus", "Helianthus", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Light neutral oil; frying, salad dressing; high in Vitamin E"),
            ("CANOLA-OIL", "Canola Oil (Rapeseed)", "Brassica napus", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "4-5 months", "Low erucic acid rapeseed oil; neutral flavor; frying, baking"),
            ("COCONUT-OIL", "Coconut Oil", "Cocos nucifera", "Cocos", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "11-12 months", "Tropical oil; high saturated fat; cooking, baking, cosmetic uses"),
            ("PALM-KERNEL-OIL", "Palm Kernel Oil", "Elaeis guineensis", "Elaeis", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "24-30 months", "Oil from palm seed; used in margarine, confectionery, soaps"),
            ("SOYBEAN-OIL", "Soybean Oil", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-6 months", "Most consumed vegetable oil in US; neutral; frying, margarine"),
            ("CORN-OIL", "Corn Oil (Maize Oil)", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Refined oil from maize germ; high smoke point; frying"),
            ("PEANUT-OIL", "Peanut Oil (Groundnut)", "Arachis hypogaea", "Arachis", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "4-5 months", "High smoke point oil; frying, Asian stir-fry; nutty flavor"),
            ("SESAME-OIL", "Sesame Oil", "Sesamum indicum", "Sesamum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Pedaliaceae", "3-4 months", "Aromatic oil; toasted for flavor; Asian cuisine, dressing"),
            ("GRAPESEED-OIL", "Grapeseed Oil", "Vitis vinifera", "Vitis", "Magnoliophyta", "Magnoliopsida", "Vitales", "Vitaceae", "4-5 months", "Light oil from wine grape seeds; high smoke point; neutral flavor"),
            ("AVOCADO-OIL", "Avocado Oil", "Persea americana", "Persea", "Magnoliophyta", "Magnoliopsida", "Laurales", "Lauraceae", "5-7 months", "Green-tinted oil; high smoke point; rich in monounsaturated fat"),
        ]
    },
    "MUSHROOMS": {
        "code": "MUSHROOMS", "description": "Edible fungi and mushrooms",
        "items": [
            ("BUTTON-MUSHROOM", "Button Mushroom", "Agaricus bisporus", "Agaricus", "Basidiomycota", "Agaricomycetes", "Agaricales", "Agaricaceae", "4-5 weeks", "Common white mushroom; raw, sautéed, soup; world's most cultivated"),
            ("SHIITAKE", "Shiitake Mushroom", "Lentinula edodes", "Lentinula", "Basidiomycota", "Agaricomycetes", "Agaricales", "Marasmiaceae", "6-8 weeks", "Umami-rich Asian mushroom; dried, fresh; medicinal properties"),
            ("OYSTER-MUSHROOM", "Oyster Mushroom", "Pleurotus ostreatus", "Pleurotus", "Basidiomycota", "Agaricomycetes", "Agaricales", "Pleurotaceae", "3-5 weeks", "Fan-shaped mushroom; delicate flavor; stir-fry, soup"),
            ("PORTOBELLO", "Portobello Mushroom", "Agaricus bisporus", "Agaricus", "Basidiomycota", "Agaricomycetes", "Agaricales", "Agaricaceae", "6-8 weeks", "Mature brown agaricus; grilled as burger; meaty texture"),
            ("ENOKI", "Enoki Mushroom", "Flammulina filiformis", "Flammulina", "Basidiomycota", "Agaricomycetes", "Agaricales", "Physalacriaceae", "4-6 weeks", "Long-stemmed white mushroom; East Asian cuisine; soups, hot pot"),
            ("CHANTERELLE", "Chanterelle", "Cantharellus cibarius", "Cantharellus", "Basidiomycota", "Agaricomycetes", "Cantharellales", "Cantharellaceae", "Seasonal", "Golden trumpet-shaped; fruity aroma; wild foraged; gourmet"),
            ("MOREL", "Morel Mushroom", "Morchella esculenta", "Morchella", "Ascomycota", "Pezizomycetes", "Pezizales", "Morchellaceae", "Seasonal", "Honeycomb cap; earthy flavor; wild foraged; highly prized"),
            ("TRUFFLE-BLACK", "Black Truffle (Périgord)", "Tuber melanosporum", "Tuber", "Ascomycota", "Pezizomycetes", "Pezizales", "Tuberaceae", "5-7 years", "Premium underground fungus; pungent aroma; shaved on dishes"),
            ("TRUFFLE-WHITE", "White Truffle (Alba)", "Tuber magnatum", "Tuber", "Ascomycota", "Pezizomycetes", "Pezizales", "Tuberaceae", "5-7 years", "Rarest truffle; garlicky aroma; served raw shaved; extremely expensive"),
            ("WOOD-EAR", "Wood Ear Mushroom", "Auricularia auricula-judae", "Auricularia", "Basidiomycota", "Agaricomycetes", "Auriculariales", "Auriculariaceae", "4-6 weeks", "Ear-shaped fungus; crunchy texture; Asian soups and stir-fry"),
            ("PORCINI", "Porcini (Cep)", "Boletus edulis", "Boletus", "Basidiomycota", "Agaricomycetes", "Boletales", "Boletaceae", "Seasonal", "Wild mushroom; nutty flavor; dried for risotto, pasta, sauces"),
            ("MAITAKE", "Maitake (Hen of Woods)", "Grifola frondosa", "Grifola", "Basidiomycota", "Agaricomycetes", "Polyporales", "Meripilaceae", "4-6 weeks", "Frilly clustered mushroom; earthy; immune-support properties"),
        ]
    },
    "SEAWEED": {
        "code": "SEAWEED", "description": "Edible seaweeds and algae",
        "items": [
            ("NORI", "Nori (Purple Laver)", "Pyropia yezoensis", "Pyropia", "Rhodophyta", "Bangiophyceae", "Bangiales", "Bangiaceae", "2-3 months", "Dried seaweed sheets; sushi wrapper; rich in iodine and B12"),
            ("KOMBU", "Kombu (Kelp)", "Saccharina japonica", "Saccharina", "Ochrophyta", "Phaeophyceae", "Laminariales", "Laminariaceae", "6-12 months", "Thick brown kelp; dashi broth base; umami from glutamic acid"),
            ("WAKAME", "Wakame", "Undaria pinnatifida", "Undaria", "Ochrophyta", "Phaeophyceae", "Laminariales", "Alariaceae", "6-9 months", "Green seaweed; miso soup, seaweed salad; rich in calcium"),
            ("SPIRULINA", "Spirulina", "Arthrospira platensis", "Arthrospira", "Cyanobacteria", "Cyanophyceae", "Oscillatoriales", "Microcoleaceae", "2-3 weeks", "Blue-green microalgae; superfood; powder supplement; high protein"),
            ("CHLORELLA", "Chlorella", "Chlorella vulgaris", "Chlorella", "Chlorophyta", "Trebouxiophyceae", "Chlorellales", "Chlorellaceae", "1-2 weeks", "Green microalgae; detox supplement; rich in chlorophyll and iron"),
            ("DULSE", "Dulse (Palmaria)", "Palmaria palmata", "Palmaria", "Rhodophyta", "Florideophyceae", "Palmariales", "Palmariaceae", "4-5 months", "Red seaweed; chewy texture; snack, seasoning; Atlantic coasts"),
            ("IRISH-MOSS", "Irish Moss (Carrageen)", "Chondrus crispus", "Chondrus", "Rhodophyta", "Florideophyceae", "Gigartinales", "Gigartinaceae", "6-9 months", "Red seaweed; carrageenan source; thickener in food, cosmetics"),
            ("KELP", "Giant Kelp (Bull Kelp)", "Macrocystis pyrifera", "Macrocystis", "Ochrophyta", "Phaeophyceae", "Laminariales", "Laminariaceae", "6-12 months", "World's largest seaweed; alginate source; fertilizer, food additive"),
        ]
    },
    "ADDITIONAL_GRAINS": {
        "code": "ADDITIONAL_GRAINS", "description": "Ancient and specialty grains",
        "items": [
            ("TEFF", "Teff", "Eragrostis tef", "Eragrostis", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "3-4 months", "Tiny Ethiopian grain; gluten-free; injera flatbread; rich in iron"),
            ("AMARANTH", "Amaranth Grain", "Amaranthus cruentus", "Amaranthus", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "3-4 months", "Pseudocereal; high protein; gluten-free; popped, porridge, flour"),
            ("BUCKWHEAT", "Buckwheat", "Fagopyrum esculentum", "Fagopyrum", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Polygonaceae", "3-4 months", "Pseudocereal; gluten-free; soba noodles, kasha, pancakes"),
            ("SPELT", "Spelt", "Triticum spelta", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Ancient wheat; nutty flavor; bread, pasta; easier to digest"),
            ("KAMUT", "Kamut (Khorasan Wheat)", "Triticum turanicum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Ancient Egyptian wheat; large kernel; buttery flavor; pasta, bread"),
            ("FARRO", "Farro (Emmer Wheat)", "Triticum dicoccum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Italian ancient wheat; chewy texture; salads, soup, risotto-style"),
            ("FREEKEH", "Freekeh (Green Wheat)", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Roasted green wheat; smoky flavor; Middle Eastern grain dish"),
            ("TRITICALE", "Triticale", "× Triticosecale", "Triticosecale", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "6-8 months", "Wheat-rye hybrid; higher protein than wheat; animal feed, flour"),
            ("FONIO", "Fonio", "Digitaria exilis", "Digitaria", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "2-3 months", "West African ancient grain; world's fastest-growing; nutty, couscous-like"),
            ("WILD-RICE", "Wild Rice", "Zizania palustris", "Zizania", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "3-4 months", "Aquatic grass seed; long black grain; nutty, chewy texture"),
            ("BLACK-RICE", "Black Rice (Forbidden Rice)", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "4-6 months", "Pigmented rice; deep purple when cooked; high anthocyanin content"),
        ]
    },
    "ADDITIONAL_FRUITS": {
        "code": "ADDITIONAL_FRUITS", "description": "Additional fruits from around the world",
        "items": [
            ("POMEGRANATE", "Pomegranate", "Punica granatum", "Punica", "Magnoliophyta", "Magnoliopsida", "Myrtales", "Lythraceae", "5-6 months", "Red arils; juice, fresh; rich in antioxidants; Middle Eastern fruit"),
            ("KIWI", "Kiwi Fruit (Chinese Gooseberry)", "Actinidia deliciosa", "Actinidia", "Magnoliophyta", "Magnoliopsida", "Ericales", "Actinidiaceae", "4-5 months", "Fuzzy brown fruit; green flesh; high Vitamin C; New Zealand export"),
            ("FIG", "Fig (Common Fig)", "Ficus carica", "Ficus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Moraceae", "4-5 months", "Sweet multiple fruit; fresh or dried; Mediterranean origin"),
            ("DATE-MEDJOOL", "Medjool Date", "Phoenix dactylifera", "Phoenix", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "5-7 months", "Premium date variety; large, soft, caramel-sweet; Middle Eastern staple"),
            ("DATE-DEGLET", "Deglet Noor Date", "Phoenix dactylifera", "Phoenix", "Magnoliophyta", "Liliopsida", "Arecales", "Arecaceae", "5-7 months", "Semi-dry date; translucent amber; Algeria/Tunisia origin"),
            ("PLUM", "European Plum", "Prunus domestica", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "3-4 months", "Stone fruit; purple skin; fresh, dried (prune), jam"),
            ("APRICOT", "Apricot", "Prunus armeniaca", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "3-4 months", "Small orange stone fruit; fresh, dried; rich in beta-carotene"),
            ("NECTARINE", "Nectarine", "Prunus persica var. nucipersica", "Prunus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "3-4 months", "Smooth-skinned peach variant; yellow/white flesh; sweet aroma"),
            ("RASPBERRY", "Red Raspberry", "Rubus idaeus", "Rubus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "2-3 months", "Red aggregate fruit; fresh, jam, frozen; high in fiber and Vitamin C"),
            ("BLACKBERRY", "Blackberry", "Rubus fruticosus", "Rubus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Rosaceae", "2-3 months", "Dark aggregate fruit; fresh, pie, jam; high antioxidant content"),
            ("CRANBERRY", "Cranberry", "Vaccinium macrocarpon", "Vaccinium", "Magnoliophyta", "Magnoliopsida", "Ericales", "Ericaceae", "3-5 months", "Tart red berry; juice, dried, sauce; urinary tract health"),
            ("GOOSEBERRY", "Gooseberry", "Ribes uva-crispa", "Ribes", "Magnoliophyta", "Magnoliopsida", "Saxifragales", "Grossulariaceae", "3-4 months", "Tart green/red berry; dessert, jam; European origin"),
            ("CURRANT-RED", "Red Currant", "Ribes rubrum", "Ribes", "Magnoliophyta", "Magnoliopsida", "Saxifragales", "Grossulariaceae", "3-4 months", "Small red berries; tart; jelly, dessert garnish"),
            ("CURRANT-BLACK", "Blackcurrant", "Ribes nigrum", "Ribes", "Magnoliophyta", "Magnoliopsida", "Saxifragales", "Grossulariaceae", "3-4 months", "Dark purple berry; high Vitamin C; cordial, jam, liqueur"),
            ("MULBERRY", "Mulberry", "Morus alba", "Morus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Moraceae", "3-4 months", "Sweet elongated fruit; white, red, black varieties; fresh, dried"),
            ("TAMARIND", "Tamarind", "Tamarindus indica", "Tamarindus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "6-7 months", "Sour pod fruit; paste, concentrate; Asian and Mexican cuisine"),
            ("RAMBUTAN", "Rambutan", "Nephelium lappaceum", "Nephelium", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Sapindaceae", "4-5 months", "Hairy red fruit; translucent sweet flesh; Southeast Asian tropical"),
            ("MANGOSTEEN", "Mangosteen", "Garcinia mangostana", "Garcinia", "Magnoliophyta", "Magnoliopsida", "Malpighiales", "Clusiaceae", "8-10 months", "Purple fruit with white segments; queen of tropical fruits"),
            ("JACKFRUIT", "Jackfruit", "Artocarpus heterophyllus", "Artocarpus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Moraceae", "6-8 months", "World's largest tree fruit; green unripe as meat substitute; ripe sweet"),
            ("BREADFRUIT", "Breadfruit", "Artocarpus altilis", "Artocarpus", "Magnoliophyta", "Magnoliopsida", "Rosales", "Moraceae", "6-8 months", "Starchy fruit; roasted, fried, boiled; Pacific island staple"),
            ("PERSIMMON", "Persimmon (Fuyu)", "Diospyros kaki", "Diospyros", "Magnoliophyta", "Magnoliopsida", "Ericales", "Ebenaceae", "4-5 months", "Orange tomato-like fruit; sweet when ripe; fresh, dried"),
            ("PRICKLY-PEAR", "Prickly Pear (Cactus Fruit)", "Opuntia ficus-indica", "Opuntia", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Cactaceae", "3-4 months", "Cactus fruit; magenta flesh; sweet, seedy; Mexican staple"),
        ]
    },
    "ADDITIONAL_VEGETABLES": {
        "code": "ADDITIONAL_VEGETABLES", "description": "Additional vegetables and culinary crops",
        "items": [
            ("EGGPLANT", "Eggplant (Aubergine)", "Solanum melongena", "Solanum", "Magnoliophyta", "Magnoliopsida", "Solanales", "Solanaceae", "3-4 months", "Purple fruit used as vegetable; baba ganoush, curry, grilled"),
            ("ZUCCHINI", "Zucchini (Courgette)", "Cucurbita pepo", "Cucurbita", "Magnoliophyta", "Magnoliopsida", "Cucurbitales", "Cucurbitaceae", "2-3 months", "Summer squash; green or yellow; grilled, sautéed, spiralized"),
            ("ASPARAGUS", "Asparagus", "Asparagus officinalis", "Asparagus", "Magnoliophyta", "Liliopsida", "Asparagales", "Asparagaceae", "2-3 years", "Green/white spear; steamed, grilled; rich in folate and Vitamin K"),
            ("ARTICHOKE", "Globe Artichoke", "Cynara cardunculus", "Cynara", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "5-7 months", "Edible flower bud; steamed, stuffed; Mediterranean delicacy"),
            ("BEETROOT", "Beetroot (Beet)", "Beta vulgaris", "Beta", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "2-3 months", "Red root vegetable; roasted, pickled, juice; rich in folate"),
            ("RADISH", "Radish", "Raphanus sativus", "Raphanus", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "1-2 months", "Spicy root; red, white, daikon; salad, pickled garnish"),
            ("TURNIP", "Turnip", "Brassica rapa subsp. rapa", "Brassica", "Magnoliophyta", "Magnoliopsida", "Brassicales", "Brassicaceae", "2-3 months", "White/purple root; roasted, mashed; greens also edible"),
            ("PARSNIP", "Parsnip", "Pastinaca sativa", "Pastinaca", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "4-5 months", "Creamy white root; sweet, nutty; roasted, soup, mash"),
            ("CELERY", "Celery", "Apium graveolens", "Apium", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Crisp green stalk; salad, soup, juice; low calorie"),
            ("FENNEL-VEG", "Fennel (Florence Fennel)", "Foeniculum vulgare var. azoricum", "Foeniculum", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Anise-flavored bulb; raw in salad, roasted; Mediterranean vegetable"),
            ("LEEK", "Leek", "Allium porrum", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "4-5 months", "Mild onion-like; soup, quiche; national symbol of Wales"),
            ("SHALLOT", "Shallot", "Allium cepa var. aggregatum", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "3-4 months", "Mild onion; clusters; French cuisine; shallot vinaigrette"),
            ("SPRING-ONION", "Spring Onion (Scallion)", "Allium fistulosum", "Allium", "Magnoliophyta", "Liliopsida", "Asparagales", "Amaryllidaceae", "2-3 months", "Immature onion with green top; garnish, salad, stir-fry"),
            ("GREEN-BEAN", "Green Bean (String Bean)", "Phaseolus vulgaris", "Phaseolus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "Unripe pods; steamed, stir-fried, canned; global vegetable"),
            ("PEA", "Garden Pea", "Pisum sativum", "Pisum", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "Round green seeds; fresh, frozen; rich in plant protein"),
            ("SNOW-PEA", "Snow Pea (Mangetout)", "Pisum sativum var. saccharatum", "Pisum", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "2-3 months", "Flat edible pod; stir-fry, salad; Asian cuisine"),
            ("OKRA", "Okra (Lady's Finger)", "Abelmoschus esculentus", "Abelmoschus", "Magnoliophyta", "Magnoliopsida", "Malvales", "Malvaceae", "2-3 months", "Mucilaginous pod; gumbo, curry, fried; African diaspora staple"),
            ("BAMBOO-SHOOT", "Bamboo Shoot", "Phyllostachys edulis", "Phyllostachys", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "2-3 months", "Young bamboo culm; crunchy; Asian stir-fry, soup, pickled"),
            ("WATER-CHESTNUT", "Water Chestnut", "Eleocharis dulcis", "Eleocharis", "Magnoliophyta", "Liliopsida", "Poales", "Cyperaceae", "4-5 months", "Crisp aquatic corm; Chinese cuisine; retains crunch when cooked"),
            ("JICAMA", "Jicama (Mexican Yam)", "Pachyrhizus erosus", "Pachyrhizus", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "5-6 months", "Crisp brown root; apple-like texture; salad, snack; Central American"),
            ("RHUBARB", "Rhubarb", "Rheum rhabarbarum", "Rheum", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Polygonaceae", "2-3 years", "Tart pink stalk; pie, compote, jam; leaves are toxic"),
            ("CHARD", "Swiss Chard (Silverbeet)", "Beta vulgaris subsp. vulgaris", "Beta", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "2-3 months", "Leafy green with colored stems; sautéed, steamed; nutrient-dense"),
        ]
    },
    "ADDITIONAL_SEAFOOD": {
        "code": "ADDITIONAL_SEAFOOD", "description": "Additional fish, shellfish and marine products",
        "items": [
            ("YELLOWFIN-TUNA", "Yellowfin Tuna", "Thunnus albacares", "Thunnus", "Chordata", "Actinopterygii", "Scombriformes", "Scombridae", "24-36 months", "Popular tuna species; sashimi, steak, canned; tropical waters"),
            ("BIGEYE-TUNA", "Bigeye Tuna", "Thunnus obesus", "Thunnus", "Chordata", "Actinopterygii", "Scombriformes", "Scombridae", "24-36 months", "Rich fatty tuna; sashimi grade; deep-water species"),
            ("MAHIMAHI", "Mahi-Mahi (Dolphinfish)", "Coryphaena hippurus", "Coryphaena", "Chordata", "Actinopterygii", "Carangiformes", "Coryphaenidae", "6-12 months", "Bright green/gold fish; firm white flesh; tropical sport fish"),
            ("SEA-BASS", "European Sea Bass", "Dicentrarchus labrax", "Dicentrarchus", "Chordata", "Actinopterygii", "Moroniformes", "Moronidae", "24-36 months", "Mediterranean white fish; grilled, baked; premium restaurant fish"),
            ("BARRAMUNDI", "Barramundi (Asian Sea Bass)", "Lates calcarifer", "Lates", "Chordata", "Actinopterygii", "Carangiformes", "Latidae", "24-36 months", "Australian/Asian fish; white flaky flesh; farmed and wild"),
            ("RED-SNAPPER", "Red Snapper", "Lutjanus campechanus", "Lutjanus", "Chordata", "Actinopterygii", "Perciformes", "Lutjanidae", "24-36 months", "Red-pink reef fish; firm white flesh; Gulf of Mexico"),
            ("HALIBUT", "Pacific Halibut", "Hippoglossus stenolepis", "Hippoglossus", "Chordata", "Actinopterygii", "Pleuronectiformes", "Pleuronectidae", "36-48 months", "Large flatfish; firm white flesh; low fat; North Pacific"),
            ("SOLE", "Dover Sole", "Solea solea", "Solea", "Chordata", "Actinopterygii", "Pleuronectiformes", "Soleidae", "24-36 months", "Flatfish; delicate white flesh; European fine dining classic"),
            ("TROUT-RAINBOW", "Rainbow Trout", "Oncorhynchus mykiss", "Oncorhynchus", "Chordata", "Actinopterygii", "Salmoniformes", "Salmonidae", "18-24 months", "Freshwater salmonid; pink flesh; farmed widely; mild flavor"),
            ("CATFISH", "Channel Catfish", "Ictalurus punctatus", "Ictalurus", "Chordata", "Actinopterygii", "Siluriformes", "Ictaluridae", "18-24 months", "American farmed fish; firm white flesh; Southern cuisine staple"),
            ("ANCHOVY", "European Anchovy", "Engraulis encrasicolus", "Engraulis", "Chordata", "Actinopterygii", "Clupeiformes", "Engraulidae", "2-3 years", "Small oily fish; salted, cured; pizza, Caesar salad, umami paste"),
            ("HERRING-ATLANTIC", "Atlantic Herring", "Clupea harengus", "Clupea", "Chordata", "Actinopterygii", "Clupeiformes", "Clupeidae", "3-5 years", "Small oily fish; pickled, kipper, sardine substitute; Baltic staple"),
            ("OYSTER-PACIFIC", "Pacific Oyster", "Magallana gigas", "Magallana", "Mollusca", "Bivalvia", "Ostreida", "Ostreidae", "18-36 months", "Cultivated oyster; raw on half-shell; briny flavor"),
            ("MUSSEL-BLUE", "Blue Mussel", "Mytilus edulis", "Mytilus", "Mollusca", "Bivalvia", "Mytilida", "Mytilidae", "12-18 months", "Dark-shelled bivalve; steamed, marinière, smoked; Atlantic"),
            ("CLAM-HARD", "Hard Clam (Quahog)", "Mercenaria mercenaria", "Mercenaria", "Mollusca", "Bivalvia", "Venerida", "Veneridae", "24-36 months", "Hard-shell clam; chowder, steamed, stuffed; Atlantic coast"),
            ("SCALLOP-SEA", "Sea Scallop", "Placopecten magellanicus", "Placopecten", "Mollusca", "Bivalvia", "Pectinida", "Pectinidae", "24-36 months", "Large scallop; sweet adductor muscle; seared, raw; premium seafood"),
            ("LOBSTER-AMERICAN", "American Lobster", "Homarus americanus", "Homarus", "Arthropoda", "Malacostraca", "Decapoda", "Nephropidae", "5-7 years", "Large clawed lobster; steamed, grilled; New England icon"),
            ("OCTOPUS-COMMON", "Common Octopus", "Octopus vulgaris", "Octopus", "Mollusca", "Cephalopoda", "Octopoda", "Octopodidae", "12-18 months", "Eight-armed cephalopod; grilled, braised; Mediterranean and Asian cuisine"),
            ("SQUID", "California Squid (Market Squid)", "Doryteuthis opalescens", "Doryteuthis", "Mollusca", "Cephalopoda", "Teuthida", "Loliginidae", "6-12 months", "Calamari; rings, grilled, stuffed; popular seafood worldwide"),
            ("ABALONE", "Pacific Abalone", "Haliotis rufescens", "Haliotis", "Mollusca", "Gastropoda", "Lepetellida", "Haliotidae", "36-48 months", "Single-shell gastropod; expensive delicacy; sliced tenderized"),
            ("EEL", "Japanese Eel (Unagi)", "Anguilla japonica", "Anguilla", "Chordata", "Actinopterygii", "Anguilliformes", "Anguillidae", "24-36 months", "Freshwater eel; kabayaki style; Japanese grilled eel over rice"),
            ("CRAYFISH", "Red Swamp Crayfish", "Procambarus clarkii", "Procambarus", "Arthropoda", "Malacostraca", "Decapoda", "Cambaridae", "4-6 months", "Freshwater crustacean; crawfish boil; Louisiana Cajun staple"),
        ]
    },
    "ADDITIONAL_HERBS_SPICES": {
        "code": "ADDITIONAL_HERBS_SPICES", "description": "Additional culinary herbs, spices and aromatics",
        "items": [
            ("DILL", "Dill", "Anethum graveolens", "Anethum", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "2-3 months", "Feathery herb; pickles, salmon, yogurt sauce; fresh or dried"),
            ("OREGANO", "Oregano", "Origanum vulgare", "Origanum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "3-4 months", "Pungent herb; pizza, pasta, Greek cuisine; dried more flavorful"),
            ("MARJORAM", "Sweet Marjoram", "Origanum majorana", "Origanum", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "3-4 months", "Delicate oregano relative; poultry, stuffing, mild flavor"),
            ("SAGE", "Common Sage", "Salvia officinalis", "Salvia", "Magnoliophyta", "Magnoliopsida", "Lamiales", "Lamiaceae", "4-5 months", "Gray-green herb; poultry stuffing, pork; earthy, slightly bitter"),
            ("TARRAGON", "French Tarragon", "Artemisia dracunculus", "Artemisia", "Magnoliophyta", "Magnoliopsida", "Asterales", "Asteraceae", "3-4 months", "Anise-flavored herb; chicken, fish, vinegar; French classic"),
            ("BAY-LEAF", "Bay Leaf (Laurel)", "Laurus nobilis", "Laurus", "Magnoliophyta", "Magnoliopsida", "Laurales", "Lauraceae", "24-36 months", "Aromatic leaf; soups, stews, braises; removed before serving"),
            ("LEMONGRASS", "Lemongrass", "Cymbopogon citratus", "Cymbopogon", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "3-4 months", "Citrusy stalk; Asian soups (tom yum), tea, curry paste"),
            ("GALANGAL", "Galangal (Thai Ginger)", "Alpinia galanga", "Alpinia", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "8-10 months", "Pungent rhizome; Thai curry paste, soup; sharper than ginger"),
            ("CARDAMOM-GREEN", "Green Cardamom", "Elettaria cardamomum", "Elettaria", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "24-36 months", "Aromatic pod; chai, biryani, baking; queen of spices"),
            ("CARDAMOM-BLACK", "Black Cardamom", "Amomum subulatum", "Amomum", "Magnoliophyta", "Liliopsida", "Zingiberales", "Zingiberaceae", "24-36 months", "Smoky pod; savory dishes; large dark brown; earthy flavor"),
            ("STAR-ANISE", "Star Anise", "Illicium verum", "Illicium", "Magnoliophyta", "Magnoliopsida", "Austrobaileyales", "Schisandraceae", "4-5 months", "Eight-pointed star; licorice flavor; Chinese five-spice, pho"),
            ("ALLSPICE", "Allspice (Jamaica Pepper)", "Pimenta dioica", "Pimenta", "Magnoliophyta", "Magnoliopsida", "Myrtales", "Myrtaceae", "5-6 months", "Dried unripe berry; cinnamon+clove+nutmeg flavor; Jamaican cuisine"),
            ("FENUGREEK", "Fenugreek", "Trigonella foenum-graecum", "Trigonella", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "3-4 months", "Maple-scented seed; curry powder, spice blend; medicinal"),
            ("ASAFOETIDA", "Asafoetida (Hing)", "Ferula assa-foetida", "Ferula", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "4-5 years", "Pungent resin; lentil dishes; garlic-like after cooking; Indian spice"),
            ("SUMAC", "Sumac", "Rhus coriaria", "Rhus", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Anacardiaceae", "3-4 months", "Sour red spice; Middle Eastern za'atar; salad, grilled meat"),
            ("JUNIPER-BERRY", "Juniper Berry", "Juniperus communis", "Juniperus", "Pinophyta", "Pinopsida", "Pinales", "Cupressaceae", "24-36 months", "Aromatic berry; gin flavoring; game meat, sauerkraut"),
            ("CELERY-SEED", "Celery Seed", "Apium graveolens", "Apium", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "3-4 months", "Tiny brown seed; celery salt, pickling, coleslaw; concentrated flavor"),
            ("CHERVIL", "Chervil (French Parsley)", "Anthriscus cerefolium", "Anthriscus", "Magnoliophyta", "Magnoliopsida", "Apiales", "Apiaceae", "2-3 months", "Delicate herb; eggs, fish, salads; French fines herbes blend"),
        ]
    },
    "ADDITIONAL_DAIRY": {
        "code": "ADDITIONAL_DAIRY", "description": "Additional dairy products and alternatives",
        "items": [
            ("GOAT-MILK", "Goat Milk", "Capra hircus", "Capra", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "12-24 months", "Goat's milk; easier to digest than cow milk; cheese, yogurt"),
            ("SHEEP-MILK", "Sheep Milk", "Ovis aries", "Ovis", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "12-24 months", "High fat and protein; pecorino, feta, ricotta; rich flavor"),
            ("BUFFALO-MILK", "Buffalo Milk", "Bubalus bubalis", "Bubalus", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "12-24 months", "High fat buffalo milk; mozzarella di bufala; rich creamy taste"),
            ("MOZZARELLA", "Mozzarella (Buffalo)", "Bubalus bubalis", "Bubalus", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Fresh soft cheese; pizza caprese, salad; stretched curd cheese"),
            ("PARMESAN", "Parmigiano-Reggiano", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Hard aged cheese; grating cheese; umami; 12-36 month aging"),
            ("FETA", "Feta Cheese", "Ovis aries", "Ovis", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Brined white cheese; crumbly, salty; Greek salad, pastry"),
            ("GOAT-CHEESE", "Goat Cheese (Chèvre)", "Capra hircus", "Capra", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Soft tangy cheese; fresh, aged, ash-coated; salads, spreads"),
            ("CREAM-CHEESE", "Cream Cheese", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Soft spreadable cheese; bagel, cheesecake; mild tangy flavor"),
            ("SOUR-CREAM", "Sour Cream", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Cultured cream; dollop on baked potato; dips, baking"),
            ("HEAVY-CREAM", "Heavy Cream (Double Cream)", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "High-fat cream; whipping, sauce, dessert; 36-40% butterfat"),
            ("ICE-CREAM", "Ice Cream (Vanilla)", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Frozen dairy dessert; churned with sugar and flavorings"),
            ("GHEE", "Ghee (Clarified Butter)", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Anhydrous milk fat; high smoke point; Indian cooking; lactose-free"),
            ("BUTTERMILK", "Buttermilk", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Fermented milk beverage; tangy; baking, marinade, Irish soda bread"),
            ("YOGURT-GREEK", "Greek Yogurt", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Strained yogurt; thick, high protein; breakfast, cooking, dip base"),
            ("WHEY", "Whey (Milk Protein)", "Bos taurus", "Bos", "Chordata", "Mammalia", "Artiodactyla", "Bovidae", "", "Liquid byproduct of cheese; protein powder, animal feed; ricotta source"),
        ]
    },
    "PROCESSED_FOODS": {
        "code": "PROCESSED_FOODS", "description": "Processed food ingredients and staples",
        "items": [
            ("TOFU", "Tofu (Bean Curd)", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "", "Soybean curd; silken, firm, extra-firm; high protein; versatile"),
            ("TEMPEH", "Tempeh", "Glycine max", "Glycine", "Magnoliophyta", "Magnoliopsida", "Fabales", "Fabaceae", "", "Fermented soybean cake; nutty, firm; Indonesian protein staple"),
            ("SEITAN", "Seitan (Wheat Gluten)", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Vital wheat gluten; meat substitute; chewy texture; high protein"),
            ("PASTA-WHEAT", "Pasta (Durum Wheat)", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Semolina pasta; spaghetti, penne, fusilli; Italian staple"),
            ("PASTA-RICE", "Rice Pasta (Gluten-Free)", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Gluten-free pasta alternative; rice flour noodles, penne"),
            ("BREAD-WHITE", "White Bread (Wheat Flour)", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Refined flour bread; soft texture; sandwich staple worldwide"),
            ("BREAD-WHOLEMEAL", "Wholemeal Bread", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Whole wheat flour bread; higher fiber; hearty texture"),
            ("NOODLES-EGG", "Egg Noodles", "Triticum aestivum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Wheat noodles with egg; lo mein, chow mein; Asian-Western fusion"),
            ("NOODLES-RICE", "Rice Noodles (Vermicelli)", "Oryza sativa", "Oryza", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Thin rice noodles; pad thai, pho; gluten-free; Southeast Asian staple"),
            ("COUSCOUS", "Couscous (Semolina)", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Steamed semolina granules; North African staple; quick cooking"),
            ("BULGUR", "Bulgur (Cracked Wheat)", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Parboiled cracked wheat; tabbouleh, pilaf; Middle Eastern staple"),
            ("SEMOLINA", "Semolina (Durum Flour)", "Triticum durum", "Triticum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Coarse durum flour; pasta, couscous, pudding; high gluten"),
            ("CORNMEAL", "Cornmeal (Maize Flour)", "Zea mays", "Zea", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Ground dried maize; polenta, cornbread, tortilla; gluten-free"),
            ("TAPIOCA", "Tapioca (Cassava Starch)", "Manihot esculenta", "Manihot", "Magnoliophyta", "Magnoliopsida", "Malpighiales", "Euphorbiaceae", "", "Cassava starch; pearls, flour, pudding; gluten-free thickener"),
            ("MAPLE-SYRUP", "Maple Syrup", "Acer saccharum", "Acer", "Magnoliophyta", "Magnoliopsida", "Sapindales", "Sapindaceae", "", "Tree sap concentrate; Grade A amber/dark; pancakes, baking, glaze"),
            ("HONEY", "Honey (Clover)", "Apis mellifera", "Apis", "Arthropoda", "Insecta", "Hymenoptera", "Apidae", "", "Bee nectar; natural sweetener; antibacterial; raw/processed"),
            ("MOLASSES", "Molasses (Black Treacle)", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "", "Sugar refining byproduct; dark syrup; baking, rum, barbecue"),
            ("AGAVE-SYRUP", "Agave Syrup (Nectar)", "Agave tequilana", "Agave", "Magnoliophyta", "Liliopsida", "Asparagales", "Asparagaceae", "", "Blue agave sweetener; low glycemic index; vegan alternative"),
            ("SUGAR-CANE", "Sugar Cane", "Saccharum officinarum", "Saccharum", "Magnoliophyta", "Liliopsida", "Poales", "Poaceae", "12-18 months", "Tall grass; sugar, molasses, rum, ethanol; tropical crop"),
            ("SUGAR-BEET", "Sugar Beet", "Beta vulgaris", "Beta", "Magnoliophyta", "Magnoliopsida", "Caryophyllales", "Amaranthaceae", "5-6 months", "White root; sucrose source; temperate alternative to cane"),
        ]
    },
}

LOCAL_NAMES_NEW = {
    "ALMOND": [("ar", "لوز"), ("hi", "बादाम"), ("fr", "Amande"), ("zh", "杏仁")],
    "WALNUT": [("ar", "جوز"), ("hi", "अखरोट"), ("fr", "Noix"), ("zh", "核桃")],
    "CASHEW": [("hi", "काजू"), ("ar", "الكاجو"), ("fr", "Noix de cajou"), ("pt", "Caju")],
    "PISTACHIO": [("ar", "فستق"), ("hi", "पिस्ता"), ("fr", "Pistache"), ("fa", "پسته")],
    "SESAME-SEED": [("ar", "سمسم"), ("hi", "तिल"), ("sw", "Ufuta"), ("zh", "芝麻")],
    "CHIA-SEED": [("es", "Semilla de chía"), ("zh", "奇亚籽"), ("fr", "Graines de chia")],
    "BEEF": [("ar", "لحم البقر"), ("hi", "गोमांस"), ("fr", "Boeuf"), ("sw", "Nyama ya ng'ombe")],
    "CHICKEN": [("ar", "دجاج"), ("hi", "मुर्गी"), ("fr", "Poulet"), ("sw", "Kuku")],
    "LAMB": [("ar", "لحم الضأن"), ("hi", "भेड़ का मांस"), ("fr", "Agneau"), ("sw", "Nyama ya kondoo")],
    "COFFEE-ARABICA": [("ar", "بن عربي"), ("fr", "Café arabica"), ("es", "Café arábica"), ("it", "Caffè arabica")],
    "COFFEE-ROBUSTA": [("fr", "Café robusta"), ("ar", "بن روبوستا"), ("vi", "Cà phê vối")],
    "TEA-GREEN": [("zh", "绿茶"), ("ja", "緑茶"), ("ar", "شاي أخضر"), ("hi", "हरी चाय")],
    "TEA-BLACK": [("zh", "红茶"), ("ar", "شاي أسود"), ("hi", "काली चाय"), ("en", "Black Tea")],
    "COCOA": [("ar", "كاكاو"), ("fr", "Cacao"), ("es", "Cacao"), ("zh", "可可")],
    "SPIRULINA": [("fr", "Spiruline"), ("zh", "螺旋藻"), ("es", "Espirulina"), ("ja", "スピルリナ")],
    "TEFF": [("am", "ጤፍ"), ("ar", "تيف"), ("en", "Teff")],
    "AMARANTH": [("es", "Amaranto"), ("hi", "राजगिरा"), ("zh", "苋米"), ("pt", "Amaranto")],
    "BUCKWHEAT": [("zh", "荞麦"), ("ja", "蕎麦"), ("fr", "Sarrasin"), ("ru", "Гречка")],
    "POMEGRANATE": [("ar", "رمان"), ("fa", "انار"), ("hi", "अनार"), ("fr", "Grenade")],
    "KIWI": [("zh", "猕猴桃"), ("ja", "キウイ"), ("ar", "كيوي"), ("fr", "Kiwi")],
    "FIG": [("ar", "تين"), ("fa", "انجیر"), ("fr", "Figue"), ("hi", "अंजीर")],
    "DATE-MEDJOOL": [("ar", "تمر المجهول"), ("fr", "Datte Medjool"), ("es", "Dátil Medjool")],
    "EGGPLANT": [("ar", "باذنجان"), ("hi", "बैंगन"), ("fr", "Aubergine"), ("ja", "茄子")],
    "ZUCCHINI": [("ar", "كوسا"), ("fr", "Courgette"), ("it", "Zucchina"), ("hi", "तुरई")],
    "OKRA": [("ar", "بامية"), ("hi", "भिंडी"), ("fr", "Gombo"), ("sw", "Bamia")],
    "YELLOWFIN-TUNA": [("ja", "キハダマグロ"), ("fr", "Thon jaune"), ("es", "Atún aleta amarilla")],
    "MAHIMAHI": [("es", "Dorado"), ("fr", "Coryphène"), ("haw", "Mahi-mahi")],
    "LOBSTER-AMERICAN": [("fr", "Homard américain"), ("es", "Langosta americana"), ("zh", "美洲龙虾")],
    "OCTOPUS-COMMON": [("ar", "أخطبوط"), ("ja", "タコ"), ("es", "Pulpo"), ("it", "Polpo")],
    "SQUID": [("ar", "حبار"), ("ja", "イカ"), ("es", "Calamar"), ("it", "Calamaro")],
    "DILL": [("ar", "شبت"), ("hi", "सोआ"), ("fr", "Aneth"), ("ru", "Укроп")],
    "OREGANO": [("ar", "أوريجانو"), ("el", "Ρίγανη"), ("it", "Origano"), ("es", "Orégano")],
    "SAGE": [("ar", "مريمية"), ("fr", "Sauge"), ("it", "Salvia"), ("es", "Salvia")],
    "CARDAMOM-GREEN": [("ar", "هيل"), ("hi", "इलायची"), ("fr", "Cardamome"), ("zh", "小豆蔻")],
    "STAR-ANISE": [("zh", "八角"), ("ar", "يانسون نجمي"), ("fr", "Anis étoilé"), ("hi", "चक्र फूल")],
    "FENUGREEK": [("ar", "حلبة"), ("hi", "मेथी"), ("fa", "شنبلیله"), ("am", "አበሽ")],
    "GOAT-MILK": [("ar", "حليب الماعز"), ("fr", "Lait de chèvre"), ("es", "Leche de cabra"), ("hi", "बकरी का दूध")],
    "MOZZARELLA": [("it", "Mozzarella di bufala"), ("ar", "موزاريلا"), ("fr", "Mozzarella")],
    "PARMESAN": [("it", "Parmigiano-Reggiano"), ("ar", "بارميزان"), ("fr", "Parmesan")],
    "FETA": [("el", "Φέτα"), ("ar", "جبنة فيتا"), ("fr", "Feta"), ("tr", "Beyaz peynir")],
    "TOFU": [("zh", "豆腐"), ("ja", "豆腐"), ("ko", "두부"), ("hi", "टोफू")],
    "HONEY": [("ar", "عسل"), ("fr", "Miel"), ("hi", "शहद"), ("sw", "Asali")],
    "MAPLE-SYRUP": [("fr", "Sirop d'érable"), ("ar", "شراب القيقب"), ("zh", "枫糖浆")],
    "SUGAR-CANE": [("ar", "قصب السكر"), ("hi", "गन्ना"), ("fr", "Canne à sucre"), ("pt", "Cana-de-açúcar")],
    "GHEE": [("hi", "घी"), ("ar", "سمن"), ("fr", "Ghee"), ("sw", "Samli")],
}

NUTRITION_NEW = {
    "ALMOND": [("Calories per 100g", "579", "kcal"), ("Protein", "21.2", "g"), ("Fat", "49.9", "g"), ("Fiber", "12.5", "g"), ("Vitamin E", "25.6", "mg")],
    "WALNUT": [("Calories per 100g", "654", "kcal"), ("Protein", "15.2", "g"), ("Fat", "65.2", "g"), ("Omega-3", "9.1", "g"), ("Fiber", "6.7", "g")],
    "CASHEW": [("Calories per 100g", "553", "kcal"), ("Protein", "18.2", "g"), ("Fat", "43.9", "g"), ("Magnesium", "292", "mg"), ("Iron", "6.7", "mg")],
    "PISTACHIO": [("Calories per 100g", "560", "kcal"), ("Protein", "20.2", "g"), ("Fat", "45.3", "g"), ("Fiber", "10.6", "g"), ("Vitamin B6", "1.7", "mg")],
    "CHIA-SEED": [("Calories per 100g", "486", "kcal"), ("Protein", "16.5", "g"), ("Fat", "30.7", "g"), ("Fiber", "34.4", "g"), ("Omega-3", "17.8", "g")],
    "FLAX-SEED": [("Calories per 100g", "534", "kcal"), ("Protein", "18.3", "g"), ("Fat", "42.2", "g"), ("Fiber", "27.3", "g"), ("Omega-3", "22.8", "g")],
    "CHICKEN": [("Calories per 100g", "165", "kcal"), ("Protein", "31", "g"), ("Fat", "3.6", "g"), ("Niacin", "14.8", "mg"), ("Vitamin B6", "0.5", "mg")],
    "BEEF": [("Calories per 100g", "250", "kcal"), ("Protein", "26", "g"), ("Fat", "15", "g"), ("Iron", "2.6", "mg"), ("Zinc", "4.5", "mg")],
    "LAMB": [("Calories per 100g", "258", "kcal"), ("Protein", "25.6", "g"), ("Fat", "16.5", "g"), ("Vitamin B12", "2.6", "µg"), ("Iron", "1.9", "mg")],
    "COCOA": [("Calories per 100g", "228", "kcal"), ("Fat", "13.7", "g"), ("Protein", "19.6", "g"), ("Fiber", "37", "g"), ("Magnesium", "499", "mg")],
    "SPIRULINA": [("Calories per 100g", "290", "kcal"), ("Protein", "57.5", "g"), ("Iron", "28.5", "mg"), ("Vitamin B12", "0", "µg"), ("Fiber", "3.6", "g")],
    "TOFU": [("Calories per 100g", "76", "kcal"), ("Protein", "8", "g"), ("Fat", "4.8", "g"), ("Calcium", "350", "mg"), ("Iron", "5.4", "mg")],
    "HONEY": [("Calories per 100g", "304", "kcal"), ("Sugar", "82.1", "g"), ("Carbohydrates", "82.4", "g"), ("Fructose", "38.5", "g")],
    "OLIVE-OIL": [("Calories per 100g", "884", "kcal"), ("Fat", "100", "g"), ("Saturated", "13.8", "g"), ("Monounsaturated", "73", "g"), ("Vitamin E", "14.4", "mg")],
    "POMEGRANATE": [("Calories per 100g", "83", "kcal"), ("Fiber", "4", "g"), ("Vitamin C", "10.2", "mg"), ("Vitamin K", "16.4", "µg"), ("Sugar", "13.7", "g")],
    "KIWI": [("Calories per 100g", "61", "kcal"), ("Vitamin C", "92.7", "mg"), ("Fiber", "3", "g"), ("Vitamin K", "40.3", "µg")],
    "EGGPLANT": [("Calories per 100g", "25", "kcal"), ("Fiber", "3", "g"), ("Potassium", "229", "mg"), ("Vitamin C", "2.2", "mg")],
    "BUTTERMILK": [("Calories per 100g", "40", "kcal"), ("Protein", "3.3", "g"), ("Calcium", "116", "mg"), ("Vitamin B12", "0.5", "µg")],
    "GHEE": [("Calories per 100g", "900", "kcal"), ("Fat", "100", "g"), ("Saturated", "62", "g"), ("Vitamin A", "840", "µg")],
    "OYSTER-PACIFIC": [("Calories per 100g", "81", "kcal"), ("Protein", "9.5", "g"), ("Zinc", "16.6", "mg"), ("Iron", "5.1", "mg"), ("Vitamin B12", "15.6", "µg")],
}


async def seed_more():
    log.info("=" * 56)
    log.info("  FoodTrack Additional Item Seed (200+)")
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

        for cat_name, cat_data in NEW_CATEGORIES.items():
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

                if code in LOCAL_NAMES_NEW:
                    for lang, lname in LOCAL_NAMES_NEW[code]:
                        db.add(ItemName(item_id=tax_item.id, language=lang, name=lname, is_primary=False))

                if code in NUTRITION_NEW:
                    for key, value, unit in NUTRITION_NEW[code]:
                        db.add(ItemAttribute(item_id=tax_item.id, key=key, value=str(value), unit=unit))

                total_new += 1
                if total_new % 20 == 0:
                    log.info(f"  ... {total_new} new items seeded so far")

        await db.commit()
        log.info(f"Seeded {total_new} NEW taxonomy items across {len([n for n in NEW_CATEGORIES if n])} categories")
        total_result = await db.execute(select(func.count(TaxonomyItem.id)))
        log.info(f"Total taxonomy items now: {total_result.scalar()}")
        log.info("Done!")


if __name__ == "__main__":
    asyncio.run(seed_more())
