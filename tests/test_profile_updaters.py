import pytest
from backend.profile_updater.updater import ProfileData


class TestProfileData:
    def test_empty_profile(self):
        p = ProfileData()
        assert not p.has_any()

    def test_headline_only(self):
        p = ProfileData(headline="Python Developer at ACME")
        assert p.has_any()
        assert p.headline == "Python Developer at ACME"

    def test_skills(self):
        p = ProfileData(skills=["Python", "Django", "AWS"])
        assert p.has_any()
        assert len(p.skills) == 3
        assert "Python" in p.skills

    def test_all_fields(self):
        p = ProfileData(
            headline="Senior Python Dev",
            about="Backend specialist",
            location="Medellin",
            skills=["Python", "SQL"],
            education=[{"degree": "BS CS", "school": "UdeA"}],
            experience=[{"title": "Dev", "company": "Co"}],
            certifications=["AWS Certified"],
            open_to_work=True,
        )
        assert p.has_any()
        assert len(p.education) == 1
        assert p.experience[0]["title"] == "Dev"
        assert p.open_to_work is True

    def test_open_to_work_false(self):
        p = ProfileData(open_to_work=False)
        assert p.has_any()

    def test_skills_empty_list(self):
        p = ProfileData(skills=[])
        assert not p.has_any()

    def test_education_empty_list(self):
        p = ProfileData(education=[])
        assert not p.has_any()
