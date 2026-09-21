from django.core.management.base import BaseCommand
from apps.library.models import CuratedBook

BOOKS = [
    # Python
    {"field_slug": "python", "title": "Automate the Boring Stuff with Python", "author": "Al Sweigart", "url": "https://automatetheboringstuff.com/", "level": "junior", "order_rank": 1},
    {"field_slug": "python", "title": "Python Crash Course", "author": "Eric Matthes", "url": "https://ehmatthes.github.io/pcc/", "level": "junior", "order_rank": 2},
    {"field_slug": "python", "title": "Fluent Python", "author": "Luciano Ramalho", "url": "https://www.oreilly.com/library/view/fluent-python-2nd/9781492126072/", "level": "senior", "order_rank": 3},
    
    # Frontend
    {"field_slug": "frontend", "title": "You Don't Know JS", "author": "Kyle Simpson", "url": "https://github.com/getify/You-Dont-Know-JS", "level": "junior", "order_rank": 1},
    {"field_slug": "frontend", "title": "JavaScript: The Definitive Guide", "author": "David Flanagan", "url": "https://www.oreilly.com/library/view/javascript-the-definitive/9781491952016/", "level": "senior", "order_rank": 2},
    {"field_slug": "frontend", "title": "Eloquent JavaScript", "author": "Marijn Haverbeke", "url": "https://eloquentjavascript.net/", "level": "junior", "order_rank": 3},
    
    # Backend Node
    {"field_slug": "backend_node", "title": "Node.js Design Patterns", "author": "Mario Casciaro", "url": "https://www.nodejsdesignpatterns.com/", "level": "mid", "order_rank": 1},
    {"field_slug": "backend_node", "title": "The Node.js Way", "author": "Felix Geisendörfer", "url": "https://github.com/felixge/node-style-guide", "level": "junior", "order_rank": 2},
    
    # Cybersecurity
    {"field_slug": "cybersecurity", "title": "The Web Application Hacker's Handbook", "author": "Stuttard & Pinto", "url": "https://www.amazon.com/Web-Application-Hackers-Handbook-Discovering/dp/1118026470", "level": "mid", "order_rank": 1},
    {"field_slug": "cybersecurity", "title": "OWASP Top 10 Guide", "author": "OWASP", "url": "https://owasp.org/www-project-top-ten/", "level": "junior", "order_rank": 2},
    {"field_slug": "cybersecurity", "title": "Cryptography Engineering", "author": "Ferguson, Schneier, Kohno", "url": "https://www.schneier.com/books/cryptography-engineering/", "level": "senior", "order_rank": 3},
    
    # Data Science
    {"field_slug": "data_science", "title": "Python for Data Analysis", "author": "Wes McKinney", "url": "https://wesmckinney.com/book/", "level": "junior", "order_rank": 1},
    {"field_slug": "data_science", "title": "Hands-On Machine Learning", "author": "Aurélien Géron", "url": "https://www.oreilly.com/library/view/hands-on-machine-learning/9781491962282/", "level": "mid", "order_rank": 2},
    
    # Machine Learning
    {"field_slug": "machine_learning", "title": "Deep Learning", "author": "Goodfellow, Bengio, Courville", "url": "https://www.deeplearningbook.org/", "level": "senior", "order_rank": 1},
    {"field_slug": "machine_learning", "title": "Machine Learning Yearning", "author": "Andrew Ng", "url": "https://www.deeplearning.ai/machine-learning-yearning/", "level": "mid", "order_rank": 2},
    
    # Deep Learning
    {"field_slug": "deep_learning", "title": "Neural Networks and Deep Learning", "author": "Michael Nielsen", "url": "http://neuralnetworksanddeeplearning.com/", "level": "junior", "order_rank": 1},
    
    # DevOps
    {"field_slug": "devops", "title": "The Phoenix Project", "author": "Gene Kim, et al", "url": "https://www.oreilly.com/library/view/the-phoenix-project/9781491951530/", "level": "mid", "order_rank": 1},
    {"field_slug": "devops", "title": "Site Reliability Engineering", "author": "Google SRE Team", "url": "https://sre.google/books/", "level": "senior", "order_rank": 2},
    
    # Digital Marketing
    {"field_slug": "digital_marketing", "title": "Traction", "author": "Gabriel Weinberg", "url": "https://www.amazon.com/Traction-Startup-Achieve-Exponential-Growth/dp/1491924969", "level": "junior", "order_rank": 1},
    {"field_slug": "digital_marketing", "title": "Growth Hacker Marketing", "author": "Sean Ellis", "url": "https://www.growthhackingbook.com/", "level": "junior", "order_rank": 2},
]


class Command(BaseCommand):
    help = "Seed curated books for search"

    def handle(self, *args, **options):
        created = 0
        for data in BOOKS:
            _, is_new = CuratedBook.objects.update_or_create(
                title=data["title"],
                field_slug=data["field_slug"],
                defaults=data
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded/updated {len(BOOKS)} curated books ({created} new)"))
