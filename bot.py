import random
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters, CallbackContext
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')

engine = create_engine(DATABASE_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True)
    from_user = Column(Integer)
    to_user = Column(Integer)
    type = Column(String)

class Submissions(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    text = Column(String)
    type = Column(String)
    status = Column(String)

Base.metadata.create_all(engine)

def save_interaction(from_user, to_user, type_, text):
    session = Session()

    interaction = Interaction(
        from_user = from_user,
        to_user = to_user,
        type = type_,
    )

    session.add(interaction)
    session.commit()
    session.close()

def get_random_submission(type_):
    session = Session()

    items = session.query(Submissions).filter_by(
        type = type_,
        status = "approved"
    ).all()

    if not items:
        return "No entries available yet."

    return random.choice([i.text for i in items])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return

    text = update.message.text.lower()

    from_user = update.message.from_user.id
    to_user = update.message.reply_to_message.from_user.id

    if "kiss" in text:
        save_interaction(from_user, to_user, "kiss", text)
        response = get_random_submission("compliment")
        await update.message.reply_text(response)

    elif "kick" in text:
        save_interaction(from_user, to_user, "kick", text)
        response = get_random_submission("insult")
        await update.message.reply_text(response)

async def submit_kiss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    session = Session()

    submission = Submissions(
        text = text,
        type = "compliment",
        status = "pending",
    )

    session.add(submission)
    session.commit()
    session.close()

    await update.message.reply_text("Compliment submitted for review ✅")

async def submit_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    session = Session()

    submission = Submissions(
        text = text,
        type = "insult",
        status = "pending",
    )

    session.add(submission)
    session.commit()
    session.close()

    await update.message.reply_text("Insult submitted for review ⚠️")

async def view_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()

    pending = session.query(Submissions).filter_by(status = "pending").all()

    if not pending:
        await update.message.reply_text("No pending submissions.")
        return

    message = "📋 Pending submissions:\n\n"

    for p in pending:
        message += f"ID: {p.id} | {p.type} | {p.text}\n"

    await update.message.reply_text(message)
    session.close()

async def approve(update:Update, context: ContextTypes.DEFAULT_TYPE):
    submission_id = int(context.args[0])

    session = Session()
    sub = session.query(Submissions).get(submission_id)
    sub.status = "approved"

    session.commit()
    session.close()

    await update.message.reply_text("Approved ✅")

async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    submission_id = int(context.args[0])
    session = Session()

    sub = session.query(Submissions).get(submission_id)
    sub.status = "rejected"

    session.commit()
    session.close()

    await update.message.reply_text("Rejected ❌")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = Session()

    user_id = update.message.from_user.id

    interactions = session.query(Interaction).filter(
        (Interaction.from_user == user_id) | (Interaction.to_user == user_id)
    ).all()

    kisses_given = 0
    kisses_received = 0
    kicks_given = 0
    kicks_received = 0

    for i in interactions:
        if i.type == "kiss":
            if i.from_user == user_id:
                kisses_given += 1
            else:
                kisses_received += 1

        elif i.type == "kick":
            if i.to_user == user_id:
                kicks_received += 1
            else:
                kicks_given += 1

    await update.message.reply_text(
        f"📊 Your Stats:\n\n"
        f"❤️ Kisses given: {kisses_given}\n"
        f"💋 Kisses received: {kisses_received}\n"
        f"👊 Kicks given: {kicks_given}\n"
        f"😵 Kicks received: {kicks_received}"
    )

    session.close()

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("submit_kiss", submit_kiss))
app.add_handler(CommandHandler("submit_kick", submit_kick))

app.add_handler(CommandHandler("pending", view_pending))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("reject", reject))

app.add_handler(CommandHandler("summary", summary))
app.run_polling()