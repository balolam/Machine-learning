# coding=utf-8
from elasticsearch import helpers
from copy import deepcopy


def split_list(_list, _count):
    result = []

    if len(_list) == 0:
        return result

    if len(_list) == _count:
        result.append(_list)

        return result

    steps = len(_list) / _count
    tmp_list = deepcopy(_list)

    for i in range(0, steps):
        result.append(tmp_list[0: _count])
        tmp_list = tmp_list[_count: len(tmp_list)]

    if len(tmp_list) != 0:
        result.append(tmp_list)

    return result


class FacebookDBCache(object):
    def __init__(self):
        self.documents = []
        self.messages = []
        self.sources = []


class NameRelation(object):
    def __init__(self, fl_name, post_id):
        self.fl_name = fl_name
        self.post_id = post_id


class FacebookDBHelper(object):
    def __init__(self, es):
        self.es = es

    def save_posts(self, index, doc_type, group_name, group_domain, posts):
        actions = []

        for post in posts:
            keys = post.keys()
            message_key_exists = 'message' in keys
            created_time_exists = 'created_time' in keys

            if message_key_exists and created_time_exists:
                action = {
                    "_index": index,
                    "_type": doc_type,
                    "_id": post['id'],
                    "_source": {
                        "message": post['message'],
                        "created_time": post['created_time'],
                        "group_name": group_name,
                        "group_domain": group_domain
                    }
                }

                actions.append(action)

        self.__bulk_insert(actions)

    def save_name_relations(self, index, doc_type, relations):
        actions = []

        for relation in relations:
            action = {
                "_index": index,
                "_type": doc_type,
                "_source": {
                    "fl_name": relation.fl_name,
                    "post_id": relation.post_id
                }
            }

            actions.append(action)

        self.__bulk_insert(actions)

    def __bulk_insert(self, actions):
        actions_list = split_list(list(actions), 500)

        for acts in actions_list:
            helpers.bulk(self.es, acts)

    def get_all_posts(self, index, doc_type):
        return self.__get_all(index=index, doc_type=doc_type)

    def get_all_name_relations(self, index, doc_type):
        relations = self.__get_all(index=index, doc_type=doc_type)

        # noinspection PyTypeChecker
        return [NameRelation(fl_name=r['_source']['fl_name'], post_id=r["_id"]) for r in relations]

    def __get_all(self,  index, doc_type):
        result = []

        page = self.es.search(
            index=index,
            doc_type=doc_type,
            scroll='2m',
            search_type='scan',
            size=1000,
            body={})

        scroll_id = page['_scroll_id']
        scroll_size = page['hits']['total']

        while scroll_size > 0:
            page = self.es.scroll(scroll_id=scroll_id, scroll='2m')

            scroll_id = page['_scroll_id']
            scroll_size = len(page['hits']['hits'])

            result.extend(page['hits']['hits'])

        return result


    def get_all_sources(self, index, doc_type):
        posts = self.get_all_posts(index=index, doc_type=doc_type)
        result = []

        for post in posts:
            if "_source" in post.keys():
                # noinspection PyTypeChecker
                result.append(post["_source"])

        return result

    def get_all_messages(self, index, doc_type):
        sources = self.get_all_sources(index=index, doc_type=doc_type)
        result = []

        for source in sources:
            if 'message' in source.keys():
                # noinspection PyTypeChecker
                result.append(source["message"])

        return result


class SimpleFacebookDBHelper(object):
    def __init__(self, es, index, post_doc_type, name_relation_doc_type):
        self.helper = FacebookDBHelper(es)
        self.index = index
        self.post_doc_type = post_doc_type
        self.name_relation_doc_type = name_relation_doc_type

    def get_all_posts(self):
        return self.helper.get_all_posts(self.index, self.post_doc_type)

    def get_all_sources(self):
        return self.helper.get_all_sources(self.index, self.post_doc_type)

    def get_all_messages(self):
        return self.helper.get_all_messages(self.index, self.post_doc_type)

    def save_posts(self, group_name, group_domain, posts):
        self.helper.save_posts(
            group_name=group_name,
            group_domain=group_domain,
            index=self.index,
            doc_type=self.post_doc_type,
            posts=posts)

    def save_name_relations(self, relations):
        self.helper.save_name_relations(
            index=self.index,
            doc_type=self.name_relation_doc_type,
            relations=relations)

    def get_all_name_relations(self):
        return self.helper.get_all_name_relations(
            index=self.index,
            doc_type=self.name_relation_doc_type)
