# AWS App Runner - Super Quick Deploy (With Your Own Database)

**You already have a database in your `.env` file, so this is even simpler!**

---

## 🚀 One-Command Deploy

```powershell
cd d:\Github Repos\Galaxy-of-Knowledge\backend
.\deploy-apprunner.ps1
```

**That's literally it!** 

The script will:
1. ✅ Use your existing database from `.env`
2. ✅ Create AWS infrastructure (IAM, ECR)
3. ✅ Upload your secrets to AWS Secrets Manager
4. ✅ Build and push Docker image
5. ✅ Deploy to App Runner
6. ✅ Give you the service URL

---

## 💰 Your Cost (Much Cheaper!)

Since you have your own database:

| Service | Monthly Cost |
|---------|--------------|
| App Runner (1 vCPU, 2GB RAM) | **$25-50** |
| ECR Storage | $1-2 |
| Secrets Manager | $1 |
| **Total** | **~$27-53/month** |

**No RDS costs!** Saves you $15-25/month. 🎉

---

## 📋 What You Need

1. ✅ AWS account with credentials configured (`aws configure`)
2. ✅ Docker running
3. ✅ Your `.env` file with `DATABASE_URL` (you already have this!)
4. ✅ Your `service_account.json` (for Vertex AI)

---

## 🎯 After Deployment

You'll get output like this:

```
Service URL: https://abc123.us-east-1.awsapprunner.com

Test your API:
  https://abc123.us-east-1.awsapprunner.com/health
  https://abc123.us-east-1.awsapprunner.com/docs
```

Then update Vercel:
```
VITE_API_URL=https://abc123.us-east-1.awsapprunner.com
VITE_ADK_URL=https://abc123.us-east-1.awsapprunner.com
```

---

## 🔧 Essential Commands

```powershell
# View logs
aws logs tail /aws/apprunner/galaxy-backend --follow

# Redeploy after code changes
docker build -t galaxy-backend:latest .
docker tag galaxy-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
aws apprunner start-deployment --service-arn $SERVICE_ARN

# Pause service (stop paying when not in use)
aws apprunner pause-service --service-arn $SERVICE_ARN

# Resume service
aws apprunner resume-service --service-arn $SERVICE_ARN
```

---

## ❓ FAQ

### Do I need to migrate my database to AWS?
**No!** The script uses your existing database from `.env`. Your database can be:
- Local PostgreSQL
- Hosted elsewhere (DigitalOcean, Heroku, etc.)
- Cloud SQL (Google Cloud)
- Any PostgreSQL database accessible via internet

### Will my database work with App Runner?
**Yes!** As long as your database is accessible from the internet (not localhost), it will work perfectly.

### What if my database is on localhost?
If your `DATABASE_URL` points to `localhost`, you'll need to either:
1. Use a cloud-hosted database, OR
2. Create an AWS RDS database: `.\deploy-apprunner.ps1 -CreateDatabase`

### Can I create an AWS RDS database if I want?
Yes! Just add the `-CreateDatabase` flag:
```powershell
.\deploy-apprunner.ps1 -CreateDatabase
```

### Do I need to change anything in my code?
**No!** Your code is already async and ready to deploy. Just run the script.

---

## 🐛 Troubleshooting

### "Cannot connect to database"
Check if your database allows connections from AWS:
- Ensure database is publicly accessible
- Check firewall rules allow connections
- Verify `DATABASE_URL` in `.env` is correct

### "AWS credentials not found"
Run: `aws configure` and enter your AWS credentials

### "Docker not running"
Start Docker Desktop

---

## 📚 More Info

- **Full Guide**: `AWS_APP_RUNNER_DEPLOYMENT.md`
- **Quick Reference**: `AWS_QUICK_DEPLOY.md`
- **Summary**: `AWS_DEPLOYMENT_SUMMARY.md`

---

**Ready?** Just run:

```powershell
.\deploy-apprunner.ps1
```

That's it! No database setup needed! 🚀
