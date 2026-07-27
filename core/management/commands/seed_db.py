from django.core.management.base import BaseCommand
from core.models import Category, CosmeticProduct, ClothingProduct

class Command(BaseCommand):
    help = 'Seeds the database with CleanGirls initial categories and products.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding CleanGirls database...')

        # 1. Create categories
        categories_data = [
            # Cosmetics
            {'name': 'Soin Visage', 'slug': 'Face Care', 'icon_name': 'Sparkles', 'store_type': 'COSMETIC'},
            {'name': 'Soin Corps', 'slug': 'Body', 'icon_name': 'Leaf', 'store_type': 'COSMETIC'},
            {'name': 'Maquillage', 'slug': 'Makeup', 'icon_name': 'Smile', 'store_type': 'COSMETIC'},
            {'name': 'Parfums', 'slug': 'Perfumes', 'icon_name': 'Flame', 'store_type': 'COSMETIC'},
            # Clothes
            {'name': 'Robes', 'slug': 'Dresses', 'icon_name': 'Shirt', 'store_type': 'CLOTHING'},
            {'name': 'Hauts', 'slug': 'Tops', 'icon_name': 'Scissors', 'store_type': 'CLOTHING'},
            {'name': 'Accessoires & Ensembles', 'slug': 'Accessories', 'icon_name': 'Compass', 'store_type': 'CLOTHING'},
        ]

        categories = {}
        for cat_info in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=cat_info['slug'],
                defaults={
                    'name': cat_info['name'],
                    'icon_name': cat_info['icon_name'],
                    'store_type': cat_info['store_type']
                }
            )
            categories[cat_info['slug']] = cat
            if created:
                self.stdout.write(f"Created category: {cat.name}")

        # 2. Seeding Cosmetics Products
        cosmetics_data = [
            {
                'id': 1,
                'name': 'Sérum Éclat Infini - Or de Kribi',
                'category': 'Face Care',
                'slug': 'serum-eclat-infini-or-de-kribi',
                'description': "Un sérum ultra-concentré à l'huile précieuse de moringa et micro-particules d'or pour raviver l'éclat naturel de la peau noire et métissée.",
                'price_fcfa': 18500,
                'image_url': 'https://images.unsplash.com/photo-1620916566398-39f1143ab7be?q=80&w=600',
                'is_new': True,
                'rating': 4.9,
                'stock_quantity': 50
            },
            {
                'id': 2,
                'name': 'Brume de Rose et Aloe de Foumban',
                'category': 'Face Care',
                'slug': 'brume-de-rose-et-aloe-de-foumban',
                'description': "Une brume hydratante rafraîchissante enrichie en extraits de rose de Damas et d'aloe vera bio pour fixer le maquillage et tonifier instantanément.",
                'price_fcfa': 9500,
                'image_url': 'https://images.unsplash.com/photo-1556228720-195a672e8a03?q=80&w=600',
                'is_new': False,
                'rating': 4.7,
                'stock_quantity': 50
            },
            {
                'id': 3,
                'name': 'Crème Veloutée Karité Hydratation 24h',
                'category': 'Body',
                'slug': 'creme-veloutee-karite-hydratation-24h',
                'description': "Nourrit intensément la peau grâce au pur beurre de karité de l'Adamaoua infusé au nectar de fleur d'hibiscus. Texture non grasse au parfum envoûtant.",
                'price_fcfa': 14000,
                'image_url': 'https://images.unsplash.com/photo-1601049541289-9b1b7bbbfe19?q=80&w=600',
                'is_new': False,
                'rating': 4.8,
                'stock_quantity': 50
            },
            {
                'id': 4,
                'name': 'Masque Argile Rose Épurant Douceur',
                'category': 'Face Care',
                'slug': 'masque-argile-rose-epurant-douceur',
                'description': "Désincruste en douceur les pores et régule le sébum tout en apaisant les tiraillements grâce à l'argile de l'Ouest et l'extrait de camomille.",
                'price_fcfa': 12500,
                'image_url': 'https://images.unsplash.com/photo-1596462502278-27bfdc403348?q=80&w=600',
                'is_new': True,
                'rating': 4.6,
                'stock_quantity': 50
            },
            {
                'id': 5,
                'name': 'Élixir Lèvres Pulpeuses - Nectar de Papaye',
                'category': 'Makeup',
                'slug': 'elixir-levres-pulpeuses-nectar-de-papaye',
                'description': "Une huile à lèvres brillante ultra-sensorielle qui repulpe et nourrit sans coller. Laisse un fini glowy et un délicieux parfum fruité.",
                'price_fcfa': 7500,
                'image_url': 'https://images.unsplash.com/photo-1612817288484-6f916006741a?q=80&w=600',
                'is_new': False,
                'rating': 4.9,
                'stock_quantity': 50
            },
            {
                'id': 6,
                'name': "Parfum de Peau - Brise d'Ébène",
                'category': 'Perfumes',
                'slug': 'parfum-de-peau-brise-debene',
                'description': "Une eau de parfum captivante aux notes boisées de santal, vanille Bourbon et une touche fleurie de jasmin nocturne, sublimant la chaleur de votre peau.",
                'price_fcfa': 35000,
                'image_url': 'https://images.unsplash.com/photo-1541643600914-78b084683601?q=80&w=600',
                'is_new': True,
                'rating': 5.0,
                'stock_quantity': 50
            }
        ]

        for prod_info in cosmetics_data:
            cat = categories[prod_info['category']]
            prod, created = CosmeticProduct.objects.get_or_create(
                id=prod_info['id'],
                defaults={
                    'category': cat,
                    'name': prod_info['name'],
                    'slug': prod_info['slug'],
                    'description': prod_info['description'],
                    'price_fcfa': prod_info['price_fcfa'],
                    'image_url': prod_info['image_url'],
                    'is_new': prod_info['is_new'],
                    'rating': prod_info['rating'],
                    'stock_quantity': prod_info['stock_quantity']
                }
            )
            if created:
                self.stdout.write(f"Created cosmetic product: {prod.name}")

        # 3. Seeding Clothes Products
        clothes_data = [
            {
                'id': 1,
                'name': 'Kaba Moderne - Rose Poudré & Or',
                'category': 'Dresses',
                'slug': 'kaba-moderne-rose-poudre-et-or',
                'description': "Une réinterprétation chic et fluide du traditionnel Kaba camerounais. En soie rose poudré fluide avec détails de broderies dorées faites main.",
                'price_fcfa': 65000,
                'image_url': 'https://images.unsplash.com/photo-1595777457583-95e059d581b8?q=80&w=600',
                'is_new': True,
                'stock_xs': 2,
                'stock_s': 4,
                'stock_m': 5,
                'stock_l': 0,
                'stock_xl': 1
            },
            {
                'id': 2,
                'name': 'Robe Ndop Impériale de Gala',
                'category': 'Dresses',
                'slug': 'robe-ndop-imperiale-de-gala',
                'description': "Chef d'œuvre haute couture combinant le tissu traditionnel Ndop de l'Ouest Cameroun à une coupe sirène moderne et asymétrique ultra-féminine.",
                'price_fcfa': 120000,
                'image_url': 'https://images.unsplash.com/photo-1566174053879-31528523f8ae?q=80&w=600',
                'is_new': True,
                'stock_xs': 0,
                'stock_s': 2,
                'stock_m': 3,
                'stock_l': 2,
                'stock_xl': 0
            },
            {
                'id': 3,
                'name': 'Top Volanté Soleil de Yaoundé',
                'category': 'Tops',
                'slug': 'top-volante-soleil-de-yaounde',
                'description': "Top à volants en satin de coton lourd couleur ocre lumineux. Parfait pour une silhouette moderne et confiante lors de vos soirées ensoleillées.",
                'price_fcfa': 28000,
                'image_url': 'https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?q=80&w=600',
                'is_new': False,
                'stock_xs': 1,
                'stock_s': 5,
                'stock_m': 6,
                'stock_l': 4,
                'stock_xl': 2
            },
            {
                'id': 4,
                'name': 'Ensemble Soie Coucher de Soleil de Kribi',
                'category': 'Accessories',
                'slug': 'ensemble-soie-coucher-de-soleil-de-kribi',
                'description': "Une parure en soie premium fluide comprenant un pantalon large palazzo et une écharpe fluide satinée. Une invitation au voyage et à l'élégance décontractée.",
                'price_fcfa': 85000,
                'image_url': 'https://images.unsplash.com/photo-1490481651871-ab68de25d43d?q=80&w=600',
                'is_new': False,
                'stock_xs': 0,
                'stock_s': 2,
                'stock_m': 3,
                'stock_l': 1,
                'stock_xl': 1
            }
        ]

        for prod_info in clothes_data:
            cat = categories[prod_info['category']]
            prod, created = ClothingProduct.objects.get_or_create(
                id=prod_info['id'],
                defaults={
                    'category': cat,
                    'name': prod_info['name'],
                    'slug': prod_info['slug'],
                    'description': prod_info['description'],
                    'price_fcfa': prod_info['price_fcfa'],
                    'image_url': prod_info['image_url'],
                    'is_new': prod_info['is_new'],
                    'stock_xs': prod_info['stock_xs'],
                    'stock_s': prod_info['stock_s'],
                    'stock_m': prod_info['stock_m'],
                    'stock_l': prod_info['stock_l'],
                    'stock_xl': prod_info['stock_xl']
                }
            )
            if created:
                self.stdout.write(f"Created clothing product: {prod.name}")

        self.stdout.write(self.style.SUCCESS('Successfully seeded CleanGirls database.'))
