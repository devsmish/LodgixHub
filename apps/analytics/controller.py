from rest_framework import generics
from rest_framework.views import APIView


class PopularSearchKeywordsView(APIView):
    pass


class MySearchHistoryView(generics.ListAPIView):
    pass


class MyViewHistoryView(generics.ListAPIView):
    pass
