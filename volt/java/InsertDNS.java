import org.voltdb.*;

public class InsertDNS extends VoltProcedure {

  public final SQLStmt sql = new SQLStmt(
      "INSERT INTO DNS VALUES (?, ?, ?, ?, ?, ?);"
  );

  public VoltTable[] run( String sender,
                          String domain,
                          String response,
                          int rrcode,
                          String clusterid)
      throws VoltAbortException {
          voltQueueSQL( sql, sender, getTransactionTime(), domain, response, rrcode, clusterid );
          voltExecuteSQL();
          return null;
      }
}
