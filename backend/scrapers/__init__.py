from .base import BaseScraper

__all__ = ["BaseScraper"]


def _import_scrapers():
    from .linkedin import LinkedInScraper
    from .wellfound import WellfoundScraper
    from .getonboard import GetOnBoardScraper
    from .computrabajo import ComputrabajoScraper
    from .indeed import IndeedScraper
    from .normalizer import JobNormalizer
    return LinkedInScraper, WellfoundScraper, GetOnBoardScraper, ComputrabajoScraper, IndeedScraper, JobNormalizer


LinkedInScraper, WellfoundScraper, GetOnBoardScraper, ComputrabajoScraper, IndeedScraper, JobNormalizer = _import_scrapers()
