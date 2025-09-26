from django.shortcuts import render
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Chating
from .serializers import ChatingSerializer

class ChatingChat(generics.ChatCreateAPIView):
    queryset = Chating.objects.all()
    serializer_class = ChatingSerializer

class ChatingDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Chating.objects.all()
    serializer_class = ChatingSerializer

class HealthCheck(APIView):
    def get(self, request):
        return Response({"status": "healthy", "service": "Messaging App"})

