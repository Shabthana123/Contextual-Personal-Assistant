from src.db_manager import DBManager
import json

class ContextManager:
    def __init__(self, db: DBManager):
        self.db = db
        self.context_keys = ["projects", "people", "themes"]  # refined context fields
        # initialize context in DB if empty
        for key in self.context_keys:
            if self.db.get_context(key) is None:
                self.db.update_context(key, json.dumps({}))

    def update_context_from_card(self, card):
        """
        Refine user context with each new card.
        - projects: envelope names
        - people: assignee frequency
        - themes: keyword frequency
        """
        # load current context
        projects = json.loads(self.db.get_context("projects") or "{}")
        people = json.loads(self.db.get_context("people") or "{}")
        themes = json.loads(self.db.get_context("themes") or "{}")

        # update projects
        if card.envelope_id:
            envelope_name = self.db.get_envelope_by_id(card.envelope_id)["name"]
            projects[envelope_name] = projects.get(envelope_name, 0) + 1

        # update people
        if card.assignee:
            people[card.assignee] = people.get(card.assignee, 0) + 1

        # update themes
        for kw in card.context_keywords:
            themes[kw] = themes.get(kw, 0) + 1

        # store back in DB
        self.db.update_context("projects", json.dumps(projects))
        self.db.update_context("people", json.dumps(people))
        self.db.update_context("themes", json.dumps(themes))

    def get_refined_context(self):
        """Return the refined context as dict"""
        return {
            "projects": json.loads(self.db.get_context("projects") or "{}"),
            "people": json.loads(self.db.get_context("people") or "{}"),
            "themes": json.loads(self.db.get_context("themes") or "{}")
        }
