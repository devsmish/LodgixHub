from rest_framework.views import APIView

from apps.security.permissions import IsAdmin


class AdminDashboardStatsView(APIView):

    permission_classes = [IsAdmin]

    def get(self, request):
        raise NotImplementedError
