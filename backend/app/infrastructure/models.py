from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, BigInteger, SmallInteger, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.infrastructure.database import Base


class SettlementTimeframe(Base):
    __tablename__ = 'Settlement_Timeframes'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Start_Date = Column(Date, nullable=True)
    Start_Slot = Column(SmallInteger, nullable=True, default=1)
    End_Date = Column(Date, nullable=True)
    End_Slot = Column(SmallInteger, nullable=True, default=96)
    Month = Column(Integer, nullable=False, default=1)
    Year = Column(Integer, nullable=False, default=2026)
    Label = Column(String(50), nullable=False)
    Status = Column(String(20), nullable=False, default='PENDING')
    Created_At = Column(DateTime, default=datetime.utcnow)
    Updated_At = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)
    variables = relationship(
        "SettlementVariables",
        back_populates="timeframe",
        uselist=False,
        cascade="all, delete-orphan")
    shutdown_windows = relationship(
        "ShutdownWindow",
        back_populates="timeframe",
        cascade="all, delete-orphan")
    custom_loss_windows = relationship(
        "CustomLossWindow",
        back_populates="timeframe",
        cascade="all, delete-orphan")


class SettlementVariables(Base):
    __tablename__ = 'Settlement_Variables'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False,
        unique=True)
    Gen_CDF_Path = Column(String(500), nullable=True)
    Con1_CDF_Path = Column(String(500), nullable=True)
    Con2_CDF_Path = Column(String(500), nullable=True)
    IEX1_Path = Column(String(500), nullable=True)
    IEX2_Path = Column(String(500), nullable=True)
    Share_Cons1 = Column(Float, nullable=False, default=30.0)
    Share_Cons2 = Column(Float, nullable=False, default=70.0)
    Cap_Share_Cons1 = Column(Float, nullable=False, default=50.0)
    Cap_Share_Cons2 = Column(Float, nullable=False, default=50.0)
    Override_Capacity_MW = Column(Float, nullable=True)
    Banked_Added_KWH = Column(Float, nullable=False, default=0.0)
    Banked_Remaining_KWH = Column(Float, nullable=False, default=0.0)
    Bank_Usage_Start_Month = Column(Integer, nullable=True)
    Bank_Usage_Start_Year = Column(Integer, nullable=True)
    Bank_Usage_End_Month = Column(Integer, nullable=True)
    Bank_Usage_End_Year = Column(Integer, nullable=True)
    Bank_Loss_Pct = Column(Float, nullable=False, default=2.0)
    Con1_PF = Column(Float, nullable=False, default=1.0)
    Con2_PF = Column(Float, nullable=False, default=1.0)
    Created_At = Column(DateTime, default=datetime.utcnow)
    Updated_At = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)
    timeframe = relationship("SettlementTimeframe", back_populates="variables")


class BankLedgerTransaction(Base):
    __tablename__ = 'Bank_Ledger_Transactions'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Consumer_Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Source_Timeframe_Id = Column(Integer, nullable=False)
    Amount_KWH = Column(Float, nullable=False)


class ShutdownWindow(Base):
    __tablename__ = 'Shutdown_Windows'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Window_Start = Column(String(20), nullable=False)
    Window_End = Column(String(20), nullable=False)
    Label = Column(String(100), nullable=True)
    Display_Order = Column(Integer, nullable=False, default=0)
    timeframe = relationship(
        "SettlementTimeframe",
        back_populates="shutdown_windows")


class CustomLossWindow(Base):
    __tablename__ = 'Custom_Loss_Windows'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Window_Start = Column(String(20), nullable=False)
    Window_End = Column(String(20), nullable=False)
    Loss_Pct = Column(Float, nullable=False)
    Display_Order = Column(Integer, nullable=False, default=0)
    timeframe = relationship(
        "SettlementTimeframe",
        back_populates="custom_loss_windows")


class User(Base):
    __tablename__ = 'Users'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Username = Column(String(100), nullable=False, unique=True)
    Password_Hash = Column(String(255), nullable=False)
    Is_Active = Column(Boolean, nullable=False, default=True)
    Created_At = Column(DateTime, default=datetime.utcnow)


class UploadSession(Base):
    __tablename__ = 'Upload_Sessions'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Uploaded_At = Column(DateTime, default=datetime.utcnow)
    File_Type = Column(String(20), nullable=False)
    Original_Filename = Column(String(255), nullable=False)
    Stored_Path = Column(String(500), nullable=False)
    File_Size_Bytes = Column(BigInteger, nullable=True)
    Blocks_Parsed = Column(Integer, nullable=True)
    Blocks_Inserted = Column(Integer, nullable=True)
    Parse_Status = Column(String(20), default='PENDING')
    Error_Message = Column(String, nullable=True)


class RawGeneratorBlock(Base):
    __tablename__ = 'Raw_Generator_Blocks'
    Id = Column(BigInteger, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Block_Date = Column(Date, nullable=False)
    Slot = Column(SmallInteger, nullable=False)
    Active_KW = Column(Float, nullable=False)
    __table_args__ = (
        Index('IX_GenBlock_Date', 'Timeframe_Id', 'Block_Date'),
    )


class RawConsumerBlock(Base):
    __tablename__ = 'Raw_Consumer_Blocks'
    Id = Column(BigInteger, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Consumer_Label = Column(String(20), nullable=False)
    Block_Date = Column(Date, nullable=False)
    Slot = Column(SmallInteger, nullable=False)
    Apparent_KVA = Column(Float, nullable=False)
    Active_KW_Raw = Column(Float, nullable=False)
    __table_args__ = (
        Index(
            'IX_ConBlock_Date',
            'Timeframe_Id',
            'Consumer_Label',
            'Block_Date'),
    )


class RawIexBlock(Base):
    __tablename__ = 'Raw_IEX_Blocks'
    Id = Column(BigInteger, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Consumer_Label = Column(String(20), nullable=False)
    Block_Date = Column(Date, nullable=False)
    Slot = Column(SmallInteger, nullable=False)
    IEX_KW = Column(Float, nullable=False, default=0.0)
    __table_args__ = (
        Index(
            'IX_IEXBlock_Date',
            'Timeframe_Id',
            'Consumer_Label',
            'Block_Date'),
    )


class CalculatedBlock(Base):
    __tablename__ = 'Calculated_Blocks'
    Id = Column(BigInteger, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Consumer_Label = Column(String(20), nullable=False)
    Block_Date = Column(Date, nullable=False)
    Slot = Column(SmallInteger, nullable=False)
    Is_Peak = Column(Boolean, nullable=False)
    Is_Shutdown = Column(Boolean, nullable=False)
    Gen_KW_Raw = Column(Float, nullable=True)
    Gen_KW_Capped = Column(Float, nullable=True)
    Consumer_KVA = Column(Float, nullable=True)
    Consumer_PF = Column(Float, nullable=True)
    IEX_KW = Column(Float, nullable=True)
    Actual_KW = Column(Float, nullable=True)
    Gen_Share_KW = Column(Float, nullable=True)
    Loss_Pct = Column(Float, nullable=True)
    Aft_KW_Main = Column(Float, nullable=True)
    Bank_In_Main = Column(Float, nullable=True)
    Net_Gen_Main = Column(Float, nullable=True)
    Aft_KW_ISO = Column(Float, nullable=True)
    Bank_In_ISO = Column(Float, nullable=True)
    Net_Gen_ISO = Column(Float, nullable=True)
    Demand_KVA = Column(Float, nullable=True)
    Discom_KVA_Block = Column(Float, nullable=True)
    __table_args__ = (
        Index(
            'IX_CalcBlock_Date',
            'Timeframe_Id',
            'Consumer_Label',
            'Block_Date'),
    )


class SettlementResult(Base):
    __tablename__ = 'Settlement_Results'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Consumer_Label = Column(String(100), nullable=False)
    Total_Gen_KWH = Column(Float, nullable=False)
    Active_Blocks = Column(Integer, nullable=False)
    Flat_KW_Allocated = Column(Float, nullable=True)
    Avg_Gen_KW = Column(Float, nullable=True)
    Prior_Sch_At_Entry_KWH = Column(Float, nullable=True)
    Sch_From_Bank_KWH = Column(Float, nullable=True)
    Revised_Gen_Allocated_KWH = Column(Float, nullable=True)
    Energy_Accountable_KWH = Column(Float, nullable=True)
    Total_Accountable_KWH = Column(Float, nullable=True)
    Bank_KWH = Column(Float, nullable=True)
    Gen_Prior_Sch_At_Exit_KWH = Column(Float, nullable=True)
    Cons_Actual_From_Gen_KWH = Column(Float, nullable=True)
    Discom_KVAH = Column(Float, nullable=True)
    Max_Demand_KVA = Column(Float, nullable=True)
    Max_Demand_Date = Column(Date, nullable=True)
    Max_Demand_Slot_Str = Column(String(30), nullable=True)
    PF_Value = Column(Float, nullable=True)
    Average_PF = Column(Float, nullable=True)
    Schedule_At_Entry_KW = Column(Float, nullable=True)
    Actual_Gen_KW = Column(Float, nullable=True)
    Revised_Sch_At_Exit_KW = Column(Float, nullable=True)
    Max_Actual_KW = Column(Float, nullable=True)
    Cons_From_Gen_KW = Column(Float, nullable=True)
    Accountable_To_Discom_KW = Column(Float, nullable=True)
    Total_Consumer_Actual_KWH = Column(Float, nullable=True)
    Calculated_At = Column(DateTime, default=datetime.utcnow)
    Calc_Duration_Seconds = Column(Float, nullable=True)


class EBCFiledValue(Base):
    __tablename__ = 'EBC_Filed_Values'
    Id = Column(Integer, primary_key=True, autoincrement=True)
    Timeframe_Id = Column(
        Integer,
        ForeignKey(
            'Settlement_Timeframes.Id',
            ondelete='CASCADE'),
        nullable=False)
    Consumer_Label = Column(String(20), nullable=False)
    Prior_Sch_Entry_KWH = Column(Float, nullable=True)
    Sch_From_Bank_KWH = Column(Float, nullable=True)
    Gen_Actual_KWH = Column(Float, nullable=True)
    Revised_Allocated_KWH = Column(Float, nullable=True)
    Energy_Accountable_KWH = Column(Float, nullable=True)
    Total_Accountable_KWH = Column(Float, nullable=True)
    Bank_KWH = Column(Float, nullable=True)
    Consumer_Actual_KWH = Column(Float, nullable=True)
    Gen_Prior_Exit_KWH = Column(Float, nullable=True)
    Gen_Realloc_Exit_KWH = Column(Float, nullable=True)
    Gen_Deviation_KWH = Column(Float, nullable=True)
    Cons_From_Gen_KWH = Column(Float, nullable=True)
    Discom_KVAH = Column(Float, nullable=True)
    Schedule_Entry_KW = Column(Float, nullable=True)
    Gen_KW = Column(Float, nullable=True)
    Revised_Exit_KW = Column(Float, nullable=True)
    Actual_Drawn_KW = Column(Float, nullable=True)
    Cons_From_Gen_KW = Column(Float, nullable=True)
    Discom_KW = Column(Float, nullable=True)
    PF_Value = Column(Float, nullable=True)
    Max_Demand_KVA = Column(Float, nullable=True)
    Provisional_Adj_KWH = Column(Float, nullable=True)
    Min_CMD_KVA = Column(Float, nullable=True)
    Updated_At = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow)
