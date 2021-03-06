import re

from datetime import datetime, timedelta

from mongoengine import Document
from mongoengine import StringField, DateTimeField

class Statistic(Document):
    d = StringField(required=True)          #device_id
    m = StringField(required=True)          #model
    v = StringField(required=True)          #version
    u = StringField(required=True)          #country
    c = StringField(required=True)          #carrier
    c_id = StringField(required=True)       #carrier_id
    t = DateTimeField(default=datetime.now) #submit_time

    meta = { "indexes": ["m", "u"] }

    field_map = {
        'device_id': 'd',
        'model': 'm',
        'version': 'v',
        'country': 'u',
        'carrier': 'c',
        'carrier_id': 'c_id',
        'submit_time': 't'
    }

class Aggregate(Document):
    d = StringField(required=True, unique=True)          #device_id
    m = StringField(required=True)          #model
    v = StringField(required=True)          #version
    u = StringField(required=True)          #country
    c = StringField(required=True)          #carrier
    c_id = StringField(required=True)       #carrier_id
    t = DateTimeField(default=datetime.now) #submit_time

    field_map = {
        'device_id': 'd',
        'model': 'm',
        'version': 'v',
        'country': 'u',
        'carrier': 'c',
        'carrier_id': 'c_id',
        'submit_time': 't'
    }

    official_regex = re.compile(r"\d{2}\.\d-\d{8}-NIGHTLY-[a-z]+")

    @classmethod
    def add_stat(cls, d, m, v, u, c, c_id):
        now = datetime.now()
        cls.objects(d=d).upsert_one(d=d, m=m, v=v, u=u, c=c, c_id=c_id, t=now).save()
        Statistic(d=d, m=m, v=v, u=u, c=c, c_id=c_id, t=now).save()

    @classmethod
    def migrate(cls):
        counter = 0
        for s in Statistic.objects().no_cache():
            stat = cls.objects(d=s.d).first()
            if not stat or stat.t < s.t:
                cls.objects(d=s.d).upsert_one(d=s.d, m=s.m, v=s.v, u=s.u, c=s.c, c_id=s.c_id, t=s.t).save()
            counter += 1
            if counter % 1000 == 0:
                print(counter)

    @classmethod
    def has_thing(cls, field, value):
        if cls.objects(**{cls.field_map[field]: value}).first():
            return True
        return False

    @classmethod
    def get_most_popular(cls, field, days):
        #> db.statistic.aggregate({ '$group': {'_id': '$d', 'model': { '$first': '$m'} } }, { '$group': { '_id': '$model', total: { '$sum': 1}}}, {'$sort': {'total': -1}})
        res = cls.objects().aggregate({ '$match': { 't': { '$gte': datetime.now()-timedelta(days=days) } } }, { '$group': {'_id': '$d', field: { '$first': '$' + cls.field_map[field] } } }, { '$group': { '_id': '$' + field, 'total': { '$sum': 1 } }}, {'$sort': {'total': -1} }, allowDiskUse=True)
        return list(res)

    @classmethod
    def get_count(cls, days=90):
        return cls.get_stats_from(days).count()

    @classmethod
    def get_stats_from(cls, days=90):
        return cls.objects(t__gte=datetime.now()-timedelta(days=days))

    @classmethod
    def get_official_count_by_field(cls, field, value, days=90):
        kwargs = {
            't__gte': datetime.now()-timedelta(days=days),
            cls.field_map[field]: value,
            'v': cls.official_regex
        }
        return cls.objects(**kwargs).count()

    @classmethod
    def get_info_by_field(cls, field, value, days=90):
        out = {}
        out['model']   = [x for x in cls.objects().aggregate({ '$match': { cls.field_map[field]: value, 't': { '$gte': datetime.now()-timedelta(days=days) }} }, { '$group': {'_id': '$d', 'models':  { '$last': '$m'} } }, { '$group': { '_id': '$models',  'total': { '$sum': 1}}}, {'$sort': {'total': -1}}, allowDiskUse=True)]
        out['version'] = [x for x in cls.objects().aggregate({ '$match': { cls.field_map[field]: value, 't': { '$gte': datetime.now()-timedelta(days=days) }} }, { '$group': {'_id': '$d', 'version': { '$last': '$v'} } }, { '$group': { '_id': '$version', 'total': { '$sum': 1}}}, {'$sort': {'total': -1}}, allowDiskUse=True)]
        out['country'] = [x for x in  cls.objects().aggregate({ '$match': { cls.field_map[field]: value, 't': { '$gte': datetime.now()-timedelta(days=days) }} }, { '$group': {'_id': '$d', 'country': { '$last': '$u'} } }, { '$group': { '_id': '$country', 'total': { '$sum': 1}}}, {'$sort': {'total': -1}}, allowDiskUse=True)]
        out['carrier'] = [x for x in cls.objects().aggregate({ '$match': { cls.field_map[field]: value, 't': { '$gte': datetime.now()-timedelta(days=days) }} }, { '$group': {'_id': '$d', 'carrier': { '$last': '$c'} } }, { '$group': { '_id': '$carrier', 'total': { '$sum': 1}}}, {'$sort': {'total': -1}}, allowDiskUse=True)]
        out['total']   = cls.objects().aggregate({ '$match': { cls.field_map[field]: value, 't': { '$gte': datetime.now()-timedelta(days=days) } } }, { '$group': { '_id': '$d' } }, { "$group": { "_id": 1, 'count': { '$sum': 1 } } }, allowDiskUse=True).next()['count']
        out['official'] = cls.get_official_count_by_field(field, value, days)
        return out

    @classmethod
    def get_field(cls, field, days=90):
        # db.statistic.aggregate({ '$group': {'_id': '$d', 'model': { '$first': '$m'} } }, { '$group': { '_id': '$model'}}
        return [x['_id'] for x in cls.objects().aggregate({ '$match': { 't': { '$gte': datetime.now()-timedelta(days=days) }} }, { '$group': {'_id': '${}'.format(cls.field_map[field])}})]
